# Comprehensive Audio Generation Service - Building Bots Network

## Mission Statement
**Excellence in audio construction and system integration** - Part of the interconnected building bots network that excels at construction and system integration, creating intelligent audio systems for the future.

## Overview

The Comprehensive Audio Generation Service is an advanced AI-powered audio generation platform that provides:

- **Multi-Model Text-to-Speech** with intelligent model selection
- **Voice Cloning and Personalization** for custom audio experiences  
- **Procedural Music Generation** with mood and style control
- **Advanced Audio Editing** and enhancement capabilities
- **Real-time Transcription** with multi-language support
- **ML-Powered Optimization** for quality and cost efficiency
- **Building Bots Network Integration** for ecosystem-wide intelligence

### Key Features

🎵 **Advanced TTS Capabilities**
- OpenAI TTS integration for premium quality
- Local models (Festival, eSpeak, Piper) for cost efficiency
- 19+ language support with native voice options
- Real-time generation with batch processing

🎤 **Voice Cloning & Enhancement**
- Reference-based voice cloning with similarity control
- Voice characteristic analysis and optimization
- Emotional tone detection and adjustment
- Age and gender estimation

🎼 **Music & Audio Generation**
- Procedural music generation with 12+ styles
- MIDI-based composition and arrangement
- Mood-based audio synthesis
- Custom instrumentation and tempo control

🔧 **Intelligent Audio Processing**
- Noise reduction and clarity enhancement
- Dynamic range compression and normalization
- Audio format conversion and optimization
- Batch editing and processing workflows

🤖 **ML-Powered Intelligence**
- User preference learning and adaptation
- Quality prediction and optimization
- Intelligent model selection algorithms
- Cost-quality balance optimization

🏗️ **Building Bots Network Integration**
- Ecosystem-wide service discovery
- Cross-service optimization and recommendations
- Global learning and knowledge sharing
- Construction excellence standards

## Quick Start

### Installation

1. **Clone and Navigate**
```bash
cd /home/activeloguser/activelog/services/audio-generation-service
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Install System Dependencies** (Ubuntu/Debian)
```bash
# TTS Engines
sudo apt-get install festival espeak espeak-data

# Audio Processing
sudo apt-get install ffmpeg portaudio19-dev

# Optional: Piper TTS
wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz
tar -xzf piper_linux_x86_64.tar.gz
sudo mv piper /usr/local/bin/
```

4. **Start Service**
```bash
python main.py
```

The service will be available at `http://localhost:8485`

### Basic Usage

```python
import requests

# Generate speech
response = requests.post("http://localhost:8485/generate/speech", json={
    "text": "Welcome to the building bots network audio system!",
    "voice_id": "alloy",
    "language": "en",
    "quality": "high",
    "enhance_audio": True
})

# Generate music
music_response = requests.post("http://localhost:8485/generate/music", json={
    "description": "Upbeat electronic music for a construction montage",
    "duration": 30.0,
    "genre": "electronic",
    "mood": "upbeat"
})

# Clone voice
with open("reference_voice.wav", "rb") as f:
    voice_response = requests.post("http://localhost:8485/clone/voice", 
        files={"reference_audio": f},
        data={
            "text": "This is a cloned voice demonstration",
            "similarity_boost": 0.8
        })
```

## API Documentation

### Base URL
```
http://localhost:8485
```

### Authentication
Currently no authentication required. API keys can be enabled via configuration.

---

## 🎵 Text-to-Speech Endpoints

### Generate Speech
Generate high-quality speech from text with intelligent optimization.

**Endpoint:** `POST /generate/speech`

**Request Body:**
```json
{
  "text": "Text to convert to speech",
  "user_id": "default",
  "voice_id": "alloy",
  "language": "en", 
  "speed": 1.0,
  "pitch": 1.0,
  "volume": 1.0,
  "format": "mp3",
  "quality": "standard",
  "model_preference": "openai-tts",
  "enhance_audio": true,
  "emotion": "neutral",
  "background_music": null
}
```

**Response:**
```json
{
  "success": true,
  "audio_id": "abc123",
  "file_path": "/tmp/generated_audio.mp3",
  "duration": 5.2,
  "format": "mp3",
  "model_used": "openai-tts",
  "quality_score": 8.7,
  "cost": 0.015,
  "generation_time": 2.1,
  "building_bots_integration": true
}
```

**Quality Levels:**
- `draft` - Fast, basic quality
- `standard` - Balanced quality and speed  
- `high` - Enhanced quality with processing
- `premium` - Maximum quality with all enhancements

**Supported Models:**
- `openai-tts` - Premium cloud-based TTS
- `piper` - High-quality neural local TTS
- `festival` - Traditional synthesis engine
- `espeak` - Lightweight multi-language TTS

### Batch Audio Generation
Generate multiple audio files efficiently.

**Endpoint:** `POST /generate/batch`

**Request Body:**
```json
{
  "texts": ["First text", "Second text", "Third text"],
  "user_id": "default",
  "base_voice_id": "nova",
  "language": "en",
  "format": "mp3",
  "priority": 5
}
```

**Response:**
```json
{
  "success": true,
  "batch_id": "batch_xyz789",
  "total_texts": 3,
  "successful_generations": 3,
  "total_cost": 0.045,
  "total_duration": 15.6,
  "batch_time": 8.2,
  "results": [
    {
      "text_index": 0,
      "result": {
        "success": true,
        "audio_id": "audio1",
        "file_path": "/tmp/batch_audio_1.mp3"
      }
    }
  ]
}
```

---

## 🎤 Voice Cloning Endpoints

### Clone Voice
Create personalized voices from reference audio samples.

**Endpoint:** `POST /clone/voice`

**Form Data:**
- `reference_audio` (file) - Reference audio sample (WAV/MP3)
- `text` (string) - Text to speak in cloned voice
- `user_id` (string) - User identifier
- `similarity_boost` (float, 0-1) - Voice similarity strength
- `stability` (float, 0-1) - Voice stability vs variation
- `style_exaggeration` (float, 0-1) - Style emphasis level

**Response:**
```json
{
  "success": true,
  "audio_id": "cloned_voice_001",
  "file_path": "/tmp/cloned_audio.wav",
  "duration": 4.8,
  "quality_score": 8.5,
  "voice_characteristics": {
    "estimated_gender": "female",
    "estimated_age_range": "young_adult",
    "emotional_tone": "calm"
  }
}
```

---

## 🎼 Music Generation Endpoints

### Generate Music
Create procedural music based on descriptions and parameters.

**Endpoint:** `POST /generate/music`

**Request Body:**
```json
{
  "description": "Uplifting orchestral piece for a construction victory",
  "user_id": "default",
  "duration": 60.0,
  "genre": "orchestral",
  "mood": "triumphant",
  "instruments": ["strings", "brass", "percussion"],
  "tempo": 120,
  "key": "C major"
}
```

**Response:**
```json
{
  "success": true,
  "audio_id": "music_gen_456",
  "file_path": "/tmp/generated_music.wav",
  "duration": 60.0,
  "format": "wav",
  "model_used": "procedural_music",
  "quality_score": 7.5,
  "composition_details": {
    "actual_tempo": 118,
    "key_signature": "C major",
    "time_signature": "4/4"
  }
}
```

**Supported Styles:**
- `ambient` - Atmospheric soundscapes
- `classical` - Traditional orchestral
- `electronic` - Synthesized music
- `jazz` - Improvisational styles
- `rock` - Energetic compositions
- `cinematic` - Film score style
- `lo-fi` - Relaxed, nostalgic
- `meditation` - Calming, peaceful

---

## 🔧 Audio Editing Endpoints

### Edit Audio
Perform various audio editing operations.

**Endpoint:** `POST /edit`

**Form Data:**
- `audio` (file) - Input audio file
- `operation` (string) - Edit operation type
- `user_id` (string) - User identifier  
- `parameters` (JSON string) - Operation parameters

**Operations & Parameters:**

**Trim Audio:**
```json
{
  "operation": "trim",
  "parameters": {
    "start_time": 5.0,
    "end_time": 30.0
  }
}
```

**Merge Audio:**
```json
{
  "operation": "merge", 
  "parameters": {
    "additional_files": ["/path/to/audio2.wav", "/path/to/audio3.wav"]
  }
}
```

**Enhance Quality:**
```json
{
  "operation": "enhance",
  "parameters": {
    "noise_reduction": true,
    "voice_clarity": true,
    "brightness": 1.1,
    "contrast": 1.2
  }
}
```

**Add Effects:**
```json
{
  "operation": "add_effects",
  "parameters": {
    "effects": ["reverb", "echo", "chorus"]
  }
}
```

**Change Speed:**
```json
{
  "operation": "change_speed",
  "parameters": {
    "speed": 1.2
  }
}
```

---

## 🎧 Transcription Endpoints

### Transcribe Audio
Convert audio to text with timestamps and translation.

**Endpoint:** `POST /transcribe`

**Form Data:**
- `audio` (file) - Audio file to transcribe
- `user_id` (string) - User identifier
- `language` (string, optional) - Expected language
- `model` (string) - Transcription model ("whisper")
- `include_timestamps` (boolean) - Include word timestamps
- `translate_to_english` (boolean) - Translate to English

**Response:**
```json
{
  "success": true,
  "transcription_id": "trans_123",
  "text": "Welcome to the comprehensive audio generation service",
  "language": "en",
  "confidence": 0.95,
  "duration": 4.2,
  "timestamps": [
    {"word": "Welcome", "start": 0.0, "end": 0.8},
    {"word": "to", "start": 0.8, "end": 0.9}
  ]
}
```

---

## 🤖 Intelligence & Analytics Endpoints

### Submit Feedback
Provide feedback to improve AI performance.

**Endpoint:** `POST /feedback`

**Request Body:**
```json
{
  "audio_id": "generated_audio_id",
  "user_id": "user123",
  "quality_score": 8.5,
  "voice_naturalness": 9.0,
  "clarity": 8.0,
  "overall_satisfaction": 8.5,
  "comments": "Great quality but could be slightly faster"
}
```

### User Analytics
Get personalized usage analytics and recommendations.

**Endpoint:** `GET /analytics/user/{user_id}`

**Response:**
```json
{
  "user_id": "user123",
  "total_generations": 45,
  "average_rating": 8.2,
  "total_audio_hours": 2.3,
  "voice_preferences": [
    {
      "voice_id": "alloy",
      "usage_count": 15,
      "average_rating": 8.7
    }
  ],
  "insights": [
    "Power user - building bots have optimized your audio experience",
    "Preferred style: professional presentations"
  ]
}
```

### System Analytics
Get comprehensive system performance metrics.

**Endpoint:** `GET /analytics/system`

**Response:**
```json
{
  "overview": {
    "total_generations": 1250,
    "unique_users": 87,
    "average_satisfaction": 8.4,
    "total_audio_hours": 125.3
  },
  "model_performance": [
    {
      "model": "openai-tts",
      "usage_count": 650,
      "avg_rating": 9.1,
      "avg_time": 2.3
    }
  ],
  "building_bots_network": {
    "mission": "Excellence in audio construction",
    "integrations": 1250,
    "network_status": "operational"
  }
}
```

---

## 📋 Information Endpoints

### Available Voices
List all available voices and their characteristics.

**Endpoint:** `GET /voices`

**Response:**
```json
{
  "voice_catalog": {
    "openai": {
      "alloy": {"gender": "neutral", "age": "adult", "style": "versatile"},
      "echo": {"gender": "male", "age": "adult", "style": "calm"}
    },
    "local": {
      "festival_male": {"gender": "male", "age": "adult", "style": "robotic"}
    }
  },
  "voice_recommendations": {
    "business": ["onyx", "alloy"],
    "storytelling": ["fable", "nova"]
  }
}
```

### Supported Languages
Get list of supported languages and regions.

**Endpoint:** `GET /languages`

**Response:**
```json
{
  "supported_languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja"],
  "total_languages": 19,
  "language_recommendations": {
    "high_quality": ["en", "es", "fr", "de"],
    "experimental": ["ar", "hi", "tr", "ko"]
  }
}
```

### Available Models
Get information about TTS models and their capabilities.

**Endpoint:** `GET /models`

**Response:**
```json
{
  "available_models": {
    "openai-tts": {
      "name": "OpenAI TTS",
      "strengths": ["high_quality", "natural_voice", "multilingual"],
      "cost_structure": "pay_per_use",
      "supported_languages": ["en", "es", "fr"],
      "available": true
    }
  },
  "selection_criteria": {
    "highest_quality": "openai-tts",
    "fastest": "espeak",
    "cost_effective": "festival"
  }
}
```

### Building Bots Mission
Get information about the building bots network integration.

**Endpoint:** `GET /building-bots/mission`

**Response:**
```json
{
  "mission": {
    "primary": "Excellence in audio construction and system integration",
    "values": ["precision", "innovation", "interconnectedness", "excellence"]
  },
  "network_status": "operational",
  "audio_specialization": {
    "tts_systems": "Advanced multi-model text-to-speech",
    "voice_cloning": "Personalized voice generation",
    "music_synthesis": "Procedural music and audio generation"
  }
}
```

---

## 🛠️ Configuration

### Environment Variables

```bash
# Service Configuration
export AUDIO_SERVICE_PORT=8485
export OPENAI_SERVICE_URL="http://localhost:8475"
export GENERATIVE_HUB_URL="http://localhost:8500" 

# Database Configuration
export AUDIO_DB_PATH="/path/to/audio_generation.db"

# Model Configuration  
export OPENAI_TTS_MODEL="tts-1-hd"
export ML_LEARNING_RATE="0.1"

# Audio Processing
export AUDIO_SAMPLE_RATE="44100"
export AUDIO_CACHE_DIR="/path/to/cache"
```

### Configuration Files

The service uses `config.py` for comprehensive configuration management:

- **ServiceConfig** - Main service settings
- **TTSModelConfig** - TTS model parameters  
- **MLConfig** - Machine learning settings
- **AudioProcessingConfig** - Audio quality settings
- **CacheConfig** - Performance caching options

---

## 🏗️ Building Bots Network Integration

This service is designed as part of the **Building Bots Network** - a system of interconnected AI services focused on construction excellence and system integration.

### Network Features

**Service Discovery**
- Automatic registration with the generative hub
- Cross-service recommendations and optimization
- Shared learning across the network

**Construction Excellence**
- Precision audio processing standards
- Quality assurance at every step
- Performance optimization algorithms

**System Integration**
- Seamless connection with image generation service
- Unified user preferences across services
- Coordinated resource management

### Hub Integration

The service automatically integrates with the generative tools hub for:
- Enhanced recommendations based on global patterns
- Cross-service user preference synchronization  
- Network-wide analytics and insights
- Coordinated cost optimization

---

## 📊 Performance & Scalability

### Performance Metrics

- **Generation Speed**: 2-5 seconds average
- **Batch Processing**: Up to 100 concurrent requests
- **Quality Scores**: 8.5+ average satisfaction
- **Uptime Target**: 99.9%

### Optimization Features

**Intelligent Caching**
- Audio file caching for repeated requests
- Model result caching for similar inputs
- User preference caching for fast recommendations

**Resource Management**
- Dynamic model selection based on load
- Queue management for batch processing
- Memory optimization for large audio files

**Cost Optimization**
- Local vs cloud model selection
- Quality vs cost balance algorithms
- Bulk processing discounts

---

## 🔍 Troubleshooting

### Common Issues

**Service Won't Start**
```bash
# Check port availability
sudo netstat -tulpn | grep :8485

# Check dependencies
python -c "import librosa, soundfile, scipy"

# Check audio tools
festival --version
espeak --version
ffmpeg -version
```

**Poor Audio Quality**
- Increase quality setting to "high" or "premium"
- Enable audio enhancement features
- Check source text for special characters
- Verify audio output device settings

**Slow Generation**
- Use local models for faster processing
- Enable caching for repeated requests  
- Reduce audio quality for speed
- Check system resources (CPU, memory)

**Model Selection Issues**
- Verify model availability with `/models` endpoint
- Check system dependencies installation
- Review configuration settings
- Test with different model preferences

### Support & Diagnostics

**Health Check**
```bash
curl http://localhost:8485/
```

**System Analytics**
```bash
curl http://localhost:8485/analytics/system
```

**Service Logs**
```bash
tail -f /home/activeloguser/activelog/services/audio-generation-service/audio_service.log
```

---

## 🚀 Advanced Features

### Voice Cloning Pipeline

1. **Reference Analysis** - Extract voice characteristics
2. **Model Training** - Create personalized voice profile  
3. **Quality Validation** - Ensure similarity and clarity
4. **Optimization** - Fine-tune for best results

### Music Generation Algorithm

1. **Description Parsing** - Extract musical elements
2. **Style Selection** - Choose appropriate generation method
3. **Composition** - Create harmonic and rhythmic patterns
4. **Arrangement** - Add instruments and effects
5. **Mastering** - Final audio processing and optimization

### ML-Powered Optimization

1. **User Pattern Analysis** - Learn individual preferences
2. **Quality Prediction** - Forecast output quality
3. **Model Selection** - Choose optimal generation method
4. **Parameter Tuning** - Adjust settings for best results
5. **Feedback Integration** - Continuous improvement

---

## 📈 Roadmap

### Upcoming Features

**Q1 2024**
- Real-time voice conversion
- Advanced emotion control
- Multi-speaker audio drama generation
- Enhanced music composition AI

**Q2 2024**  
- 3D spatial audio generation
- Voice-to-voice conversion
- Advanced audio restoration
- Mobile app integration

**Q3 2024**
- Neural voice synthesis models
- Advanced music AI collaboration
- Augmented reality audio
- Professional studio integration

### Building Bots Network Evolution

- **Expanded Ecosystem** - Integration with more specialized services
- **Advanced Intelligence** - Cross-domain learning and optimization
- **Construction Excellence** - Industry-grade reliability and precision
- **Global Network** - Worldwide deployment and localization

---

## 📞 Support

For technical support, feature requests, or building bots network integration:

- **Service Health**: `GET /` endpoint
- **System Analytics**: `GET /analytics/system` 
- **Network Status**: `GET /building-bots/mission`
- **Documentation**: This README and API endpoints

---

**Building Bots Network - Excellence in Audio Construction and System Integration**

*Precision. Innovation. Interconnectedness. Excellence.*