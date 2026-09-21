# Adaptive Computer Vision Training System

An advanced self-improving AI system that learns from user voice commands and feedback to continuously improve fish species identification accuracy. This system enables fishermen to train computer vision models by simply talking to their camera about what they're catching.

## 🎯 Core Concept

**"The fisherman is the teacher"** - Instead of requiring pre-labeled datasets, this system learns directly from fishermen's expertise through:

- **Voice Commands**: "That left tote is for king salmon, the right one is for coho"
- **Real-time Learning**: AI watches where fish go and learns the correct species
- **Continuous Feedback**: "Actually, that's a steelhead, not a salmon"
- **Personalized Models**: Each boat/fisherman gets their own optimized model

## 🚀 Key Features

### 1. Voice-Controlled Training
- Natural language processing for fishing terminology
- Species assignment through voice commands
- Real-time correction capabilities
- Context-aware command interpretation

### 2. Self-Supervised Learning
- Learns from tote placement (where fish actually go)
- No manual labeling required
- Continuous model improvement
- Automatic data collection

### 3. Personalized Adaptation
- Individual models for each user/boat
- Environmental context learning
- Fishing style adaptation
- Equipment-specific optimization

### 4. Real-Time Processing
- Live camera feed analysis
- Instant species predictions
- Fish tracking across frames
- Performance feedback loops

## 🏗️ System Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Camera Feed       │    │  Voice Commands      │    │  FishingLog Pro     │
│                     │    │                      │    │                     │
│  • Live video       │    │  • Species assignment│    │  • Trip logging     │
│  • Fish detection   │────┤  • Corrections       │────┤  • Photo management │
│  • Tracking         │    │  • Training control  │    │  • User profiles    │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                      │
                    ┌──────────────────▼──────────────────┐
                    │        Adaptive CV Training         │
                    │                                     │
                    │  • Real-time Processor             │
                    │  • Voice Training Interface        │
                    │  • Continuous Learning Engine      │
                    │  • Personalized Training System    │
                    └─────────────────────────────────────┘
```

## 📋 Component Overview

### Core Components

1. **`main.py`** - Main adaptive CV training system with WebSocket API
2. **`real_time_processor.py`** - Live camera processing and fish detection
3. **`voice_training_interface.py`** - Advanced voice command processing
4. **`continuous_learning_engine.py`** - Self-improving ML pipeline
5. **`personalized_training_system.py`** - User-specific model adaptation
6. **`fishinglog_integration.py`** - Integration with existing FishingLog system

### Key Classes

- **`AdaptiveCVTrainingSystem`** - Main orchestrator
- **`VoiceCommandProcessor`** - Processes natural language commands
- **`AdaptiveFishClassifier`** - Self-improving neural network
- **`RealTimeFishDetector`** - Live video processing
- **`PersonalizedModelManager`** - User-specific adaptations
- **`ContinuousLearningEngine`** - Automated improvement pipeline

## 🎮 Usage Examples

### Starting a Training Session

```python
from main import AdaptiveCVTrainingSystem

# Initialize system
cv_system = AdaptiveCVTrainingSystem()

# Start training session
session_id = await cv_system.start_training_session("captain_john", "fishing_vessel_1")
```

### Voice Commands

The system understands natural fishing language:

```
"That left tote is for king salmon"
"The right cooler is for coho"
"Actually, that's a steelhead, not a salmon"
"Start training"
"That was a good catch identification"
```

### Integration with FishingLog

```python
from fishinglog_integration import setup_fishinglog_integration

# Setup automatic integration
integration = await setup_fishinglog_integration(
    fishinglog_api_url="http://localhost:3000/api",
    cv_training_api_url="http://localhost:8100/api"
)
```

## 🔧 Installation

### Prerequisites

- Python 3.8+
- CUDA-capable GPU (recommended)
- Camera/video input
- Microphone for voice commands

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Hardware Requirements

- **Minimum**: 8GB RAM, CPU with 4+ cores
- **Recommended**: 16GB RAM, NVIDIA GPU with 8GB+ VRAM
- **Camera**: 1080p or higher resolution
- **Audio**: Clear microphone for voice commands

## 🚀 Quick Start

1. **Start the Main Service**
   ```bash
   python main.py
   ```

2. **Connect Camera and Start Training**
   ```python
   from real_time_processor import AdaptiveLearningPipeline
   
   pipeline = AdaptiveLearningPipeline(cv_system)
   await pipeline.start_session(session_id)
   ```

3. **Use Voice Commands**
   - Point camera at your fishing setup
   - Say: "That left tote is for king salmon"
   - Start fishing and let the AI learn!

## 📊 Performance Tracking

The system tracks various metrics:

- **Accuracy improvements over time**
- **Species-specific performance**
- **User correction patterns**
- **Environmental learning progress**
- **Model adaptation effectiveness**

### View Performance

```python
# Get user performance
performance = await cv_system.get_user_performance("captain_john")

# Get training suggestions
suggestions = await cv_system.suggest_training_focus("captain_john")
```

## 🎯 Training Workflow

1. **Setup Phase**
   - Fisherman tells system about tote arrangement
   - System creates personalized model
   - Camera starts monitoring

2. **Learning Phase**
   - AI predicts species in real-time
   - Fisherman places fish in correct totes
   - System learns from placement patterns
   - Voice corrections provide immediate feedback

3. **Improvement Phase**
   - Model accuracy improves with each trip
   - Personalized adaptations develop
   - Environmental patterns are learned
   - Performance metrics tracked

## 🔌 API Endpoints

### Training Sessions
- `POST /api/start-session` - Start new training session
- `GET /api/session/{id}/stats` - Get session statistics
- `POST /api/session/{id}/frame` - Process frame with predictions

### Voice Commands
- `WebSocket /ws/{session_id}` - Real-time voice command processing

### Performance
- `GET /api/user/{id}/performance` - Get user performance metrics
- `GET /api/user/{id}/suggestions` - Get training suggestions

## 🛠️ Configuration

### System Configuration

```python
# Voice processing settings
VOICE_CONFIG = {
    'whisper_model': 'base',
    'confidence_threshold': 0.7,
    'language': 'en'
}

# Training parameters
TRAINING_CONFIG = {
    'batch_size': 32,
    'learning_rate': 0.001,
    'update_frequency': 10
}
```

### Species Vocabulary

The system knows common fishing terminology:

```python
SPECIES_KEYWORDS = {
    'king_salmon': ['king', 'chinook', 'spring', 'tyee'],
    'coho_salmon': ['coho', 'silver', 'silvers'],
    'steelhead': ['steelhead', 'steel head'],
    # ... extensive vocabulary
}
```

## 📈 Performance Benefits

### Traditional Approach
- Requires thousands of pre-labeled images
- Generic models for all users
- Static accuracy that doesn't improve
- No personalization

### Adaptive CV Training
- **Zero pre-labeling required**
- **Personalized models** for each user
- **Continuous improvement** with each trip
- **99%+ accuracy possible** with sufficient training

## 🔄 Integration Points

### FishingLog Pro
- Automatic catch photo processing
- Training data from logged catches
- User profile synchronization
- Performance tracking

### Hardware Integration
- IP cameras
- Marine electronics
- GPS systems
- Environmental sensors

## 🐛 Troubleshooting

### Common Issues

1. **Low Accuracy**
   - Ensure good camera quality
   - Provide more voice corrections
   - Check lighting conditions

2. **Voice Commands Not Recognized**
   - Check microphone settings
   - Speak clearly and use fishing terminology
   - Verify species vocabulary matches

3. **Slow Learning**
   - Increase training frequency
   - Provide more diverse examples
   - Check model adaptation settings

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# View training progress
stats = await cv_system.get_session_stats(session_id)
print(f"Total corrections: {stats['total_corrections']}")
```

## 🚢 Deployment

### Single Vessel Deployment

```bash
# Start all services
docker-compose up -d
```

### Fleet Deployment

- Central model management
- Federated learning across vessels
- Performance benchmarking
- Fleet-wide insights

## 📚 Advanced Features

### Meta-Learning
- Fast adaptation to new species
- Few-shot learning capabilities
- Transfer learning between users

### Environmental Context
- Location-based species predictions
- Seasonal pattern learning
- Weather condition adjustments

### Active Learning
- Intelligent example selection
- Uncertainty-based sampling
- Diversity maintenance

## 🤝 Contributing

Contributions welcome! Key areas:

- Species vocabulary expansion
- New voice command patterns
- Model architecture improvements
- Integration with other marine systems

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Marine biologists for species expertise
- Commercial fishermen for real-world validation
- Computer vision research community
- Open source ML ecosystem

---

**"Teaching AI through experience, one fish at a time"** 🐟🤖