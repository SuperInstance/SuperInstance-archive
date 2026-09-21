# Comprehensive Video Generation Service - Building Bots Network

Advanced AI-powered video generation service with Runway ML, Stable Video, and Luma AI integration, intelligent content analysis, batch processing, and ML-driven optimization. Part of the Building Bots Network mission for excellence in video construction.

## 🌟 Features

### Core Video Generation
- **Multiple AI Models**: Integration with Runway ML, Stable Video Diffusion, and Luma AI
- **Text-to-Video**: Generate videos from text prompts with intelligent optimization
- **Image-to-Video**: Convert images to dynamic videos with motion effects
- **Style Detection**: Automatic style classification and optimization
- **Quality Tiers**: Draft, standard, high, and professional quality options
- **Format Support**: MP4, WebM, GIF, MOV output formats

### Advanced Video Editing
- **Comprehensive Editing**: Trim, merge, effects, transitions, enhancement
- **Visual Effects**: Color grading, blur, sharpen, vintage, sepia, film grain
- **Transitions**: Fade, slide, zoom, crossfade, wipe, dissolve effects
- **Audio Processing**: Normalization, fade in/out, noise reduction
- **Format Conversion**: Support for MP4, WebM, AVI, MOV, MKV, GIF
- **Video Compression**: Intelligent compression with quality preservation

### AI-Powered Intelligence
- **Content Analysis**: Scene detection, object recognition, motion analysis
- **Quality Assessment**: Visual quality scoring and improvement recommendations
- **Engagement Prediction**: ML-based engagement potential analysis
- **Style Optimization**: Intelligent style matching and enhancement
- **Cost Optimization**: Smart model selection for cost-quality balance
- **User Learning**: Personalized preferences and recommendation engine

### Batch Processing
- **Efficient Workflows**: Process multiple videos simultaneously
- **Queue Management**: Priority-based job scheduling
- **Progress Tracking**: Real-time status monitoring
- **Compilation Creation**: Automatic compilation video generation
- **Resource Management**: Intelligent workload distribution

### Building Bots Network Integration
- **Hub Integration**: Seamless integration with generative hub at localhost:8500
- **Cross-Service Learning**: Share insights with other network services
- **Excellence Standards**: Aligned with network construction excellence mission
- **Network Optimization**: Leverage network-wide intelligence
- **Mission Alignment**: Production-ready output with continuous improvement

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- FFmpeg installed
- MoviePy dependencies
- OpenCV for video processing
- SQLite for data storage

### Installation

1. **Navigate to service directory**:
   ```bash
   cd /home/activeloguser/activelog/services/video-generation-service
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the service**:
   ```bash
   python main.py
   # Or use the startup script
   chmod +x start_service.sh
   ./start_service.sh
   ```

4. **Verify service health**:
   ```bash
   curl http://localhost:8481/
   ```

## 📚 API Documentation

### Core Endpoints

#### Video Generation

**Generate Video from Text**
```bash
POST /generate/video
Content-Type: application/json

{
  "prompt": "A cinematic shot of a futuristic city at sunset",
  "user_id": "user123",
  "style": "cinematic",
  "duration": 10,
  "quality": "high",
  "resolution": "1920x1080",
  "model_preference": "runway-ml"
}
```

**Text-to-Video Presentation**
```bash
POST /generate/text-to-video
Content-Type: application/json

{
  "text_content": "Welcome to our product showcase...",
  "user_id": "user123",
  "video_style": "presentation",
  "duration_per_section": 3,
  "background_type": "animated"
}
```

**Image-to-Video Conversion**
```bash
POST /generate/image-to-video
Content-Type: multipart/form-data

image: [uploaded file]
user_id: user123
duration: 5
motion_type: zoom_pan
style: cinematic
add_effects: true
```

#### Batch Processing

**Submit Batch Job**
```bash
POST /generate/batch
Content-Type: application/json

{
  "requests": [
    {"prompt": "Video 1", "duration": 5},
    {"prompt": "Video 2", "duration": 8}
  ],
  "user_id": "user123",
  "priority": 7,
  "create_compilation": true
}
```

**Check Batch Status**
```bash
GET /batch/status/{batch_id}
```

**Get Batch History**
```bash
GET /batch/history/{user_id}?limit=10
```

#### Video Editing

**Edit Video**
```bash
POST /edit/video
Content-Type: multipart/form-data

video: [uploaded file]
operations: {
  "trim": {"start": 0, "end": 10},
  "effects": [{"name": "color_grade", "parameters": {"brightness": 0.1}}],
  "optimize": {"enhance_colors": true}
}
user_id: user123
```

**Merge Videos**
```bash
POST /edit/merge
Content-Type: multipart/form-data

video_files: [multiple uploaded files]
merge_params: {
  "transition": "fade",
  "transition_duration": 1.0
}
```

**Compress Video**
```bash
POST /edit/compress
Content-Type: multipart/form-data

video: [uploaded file]
compression_params: {
  "quality": "medium",
  "bitrate": "2M",
  "format": "mp4"
}
```

#### Analysis & Optimization

**Analyze Video**
```bash
POST /analyze/video
Content-Type: multipart/form-data

video: [uploaded file]
analysis_types: ["content", "quality", "engagement"]
```

**Optimize Parameters**
```bash
POST /optimize/parameters
Content-Type: multipart/form-data

prompt: "A beautiful landscape video"
user_id: user123
style: cinematic
duration: 10
quality: standard
```

#### Analytics

**User Analytics**
```bash
GET /analytics/user/{user_id}
```

**System Analytics**
```bash
GET /analytics/system
```

**Model Performance**
```bash
GET /models/performance
```

#### Building Bots Network

**Hub Status**
```bash
GET /hub/status
```

**Hub Insights**
```bash
GET /hub/insights
```

### Response Format

All endpoints return JSON responses with the following structure:

```json
{
  "success": true,
  "generation_id": "uuid-here",
  "model_used": "runway-ml",
  "quality_score": 8.5,
  "generation_time": 15.2,
  "cost": 2.50,
  "video_url": "http://localhost:8481/videos/filename.mp4",
  "metadata": {
    "resolution": "1920x1080",
    "duration": 10,
    "format": "mp4"
  },
  "hub_integration": {
    "active": true,
    "enhancements_applied": ["hub_recommended_model", "network_optimization"]
  }
}
```

## 🎨 Supported Styles

- **Cinematic**: Professional film-like quality with dramatic lighting
- **Documentary**: Realistic, natural lighting, informative
- **Animation**: Stylized, vibrant, cartoon-like
- **Commercial**: Polished, brand-focused, high production value
- **Social Media**: Trendy, engaging, optimized for sharing
- **Educational**: Clear, instructional, easy to follow
- **Artistic**: Creative, experimental, unique perspectives
- **Corporate**: Professional, clean, business-appropriate
- **Entertainment**: Dynamic, exciting, captivating
- **Lifestyle**: Relatable, authentic, personal

## 🤖 AI Models

### Runway ML
- **Strengths**: Photorealistic, creative, detailed
- **Best For**: Cinematic content, commercial videos, UI mockups
- **Cost Structure**: Pay per second of generated video
- **Quality**: Excellent (8.5/10)

### Stable Video Diffusion  
- **Strengths**: Artistic, fast, customizable, batch-friendly
- **Best For**: Artistic content, animation, concept art
- **Cost Structure**: Free (local processing)
- **Quality**: Good (7.0/10)

### Luma AI
- **Strengths**: Fast processing, good quality, social media optimized
- **Best For**: Social media content, quick videos, lifestyle
- **Cost Structure**: Pay per second
- **Quality**: Very Good (7.8/10)

## 📊 Quality Optimization

### Automatic Optimization
- **Style Detection**: Analyzes prompts for optimal style selection
- **Model Selection**: Chooses best model based on content and preferences  
- **Parameter Tuning**: Optimizes duration, resolution, effects automatically
- **Cost-Quality Balance**: Finds optimal settings for budget and quality goals
- **User Learning**: Adapts to user preferences over time

### Quality Metrics
- **Visual Quality**: Sharpness, color accuracy, composition
- **Content Relevance**: How well video matches the prompt
- **Engagement Prediction**: Likelihood of viewer engagement
- **Technical Quality**: Compression efficiency, compatibility
- **Production Readiness**: Professional standards compliance

## 🔄 Batch Processing

### Features
- **Concurrent Processing**: Multiple videos generated simultaneously
- **Priority Queue**: High-priority jobs processed first  
- **Progress Tracking**: Real-time status updates
- **Automatic Compilation**: Creates combined video from batch results
- **Resource Management**: Intelligent CPU/GPU utilization
- **Failure Handling**: Robust error handling and recovery

### Queue Management
- **Maximum Concurrent Jobs**: 3 system-wide, 2 per user
- **Priority Levels**: 1-10 (10 = highest priority)
- **Estimated Completion**: Time predictions based on queue and complexity
- **Cancellation**: Users can cancel pending or running jobs

## 🏗️ Building Bots Network Integration

### Network Mission Alignment
- **Construction Excellence**: Focus on production-ready video output
- **Continuous Learning**: Cross-service knowledge sharing
- **System Integration**: Seamless collaboration with other network services
- **Performance Optimization**: Network-wide efficiency improvements

### Hub Integration Features
- **Service Registration**: Automatic registration with generative hub
- **Recommendation Engine**: Hub-powered optimal parameter suggestions
- **Cross-Service Learning**: Share user preferences and performance data
- **Network Optimization**: Leverage network-wide intelligence
- **Mission Compliance**: Aligned with network excellence standards

### Network Contributions
- **Quality Standards**: Maintain high production quality standards
- **User Experience**: Optimize for user satisfaction and efficiency
- **Cost Optimization**: Smart resource usage and cost management
- **Knowledge Sharing**: Contribute insights to network learning

## 💾 Data Management

### Database Schema
- **Video Generations**: Complete generation history and metadata
- **User Preferences**: Learning data for personalized recommendations
- **Model Performance**: Tracking statistics for optimization
- **Batch Jobs**: Batch processing status and results
- **Video Analysis**: Content analysis and quality metrics

### Data Privacy
- **User Control**: Users control their data and preferences
- **Secure Storage**: Local SQLite database with proper security
- **Network Sharing**: Only anonymized insights shared with network
- **Data Retention**: Configurable retention policies

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8481 | Service port |
| `HUB_URL` | http://localhost:8500 | Generative hub URL |
| `MAX_CONCURRENT_JOBS` | 3 | Max concurrent batch jobs |
| `DEFAULT_QUALITY` | standard | Default video quality |
| `ENABLE_HUB_INTEGRATION` | true | Enable hub integration |

### Model Configuration
- **Runway ML**: Requires API key (set in environment)
- **Stable Video**: Local installation required
- **Luma AI**: Requires API key (set in environment)

## 📈 Monitoring & Analytics

### System Metrics
- **Generation Statistics**: Total videos, success rate, average time
- **Model Performance**: Quality scores, costs, success rates by model
- **User Satisfaction**: Feedback scores and preferences
- **Batch Processing**: Queue status, throughput, efficiency
- **Network Integration**: Hub connectivity, cross-service collaboration

### Health Checks
- **Service Health**: Basic operational status
- **Model Availability**: AI service connectivity
- **Database Status**: Data storage health
- **Hub Integration**: Network connectivity
- **Resource Usage**: CPU, memory, storage monitoring

## 🛠️ Development

### Project Structure
```
video-generation-service/
├── main.py                    # FastAPI service and core endpoints
├── video_editor.py           # Advanced video editing capabilities
├── batch_processor.py        # Batch processing system
├── video_intelligence.py     # ML-driven analysis and optimization
├── hub_integration.py        # Building Bots Network integration
├── requirements.txt          # Python dependencies
├── start_service.sh         # Service startup script
├── README.md               # This documentation
└── video_generation.db    # SQLite database
```

### Testing
```bash
# Install development dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

### Code Quality
```bash
# Format code
black *.py

# Lint code  
flake8 *.py

# Type checking
mypy *.py
```

## 🚀 Deployment

### Production Setup
1. **Set up environment variables**
2. **Configure AI service credentials**  
3. **Set up process manager** (PM2, systemd)
4. **Configure reverse proxy** (nginx)
5. **Set up monitoring** (logs, metrics)

### Scaling
- **Horizontal**: Run multiple service instances
- **Vertical**: Increase CPU/GPU resources for processing
- **Queue Management**: Adjust concurrent job limits
- **Model Distribution**: Load balance across different AI services

## 🤝 Building Bots Network

This service is part of the Building Bots Network mission for construction excellence. The network focuses on:

- **Excellence in Construction**: Every video meets production-ready standards
- **Seamless Integration**: Works harmoniously with image generation, audio synthesis, and other network services
- **Continuous Learning**: Improves through cross-service knowledge sharing
- **User-Centric Design**: Optimized for user satisfaction and efficiency
- **Mission Alignment**: Contributes to the network's construction excellence goals

## 📞 Support

For issues, questions, or feature requests:

1. **Check the troubleshooting section** in this README
2. **Review API documentation** for proper usage
3. **Monitor service logs** for error details
4. **Check hub integration status** for network issues
5. **Contact the Building Bots Network team** for network-wide concerns

## 🎯 Roadmap

### Upcoming Features
- **Real-time Video Processing**: Live video generation and editing
- **Advanced AI Models**: Integration with newer video generation models
- **Enhanced Network Features**: Deeper Building Bots Network integration
- **Mobile API**: Optimized endpoints for mobile applications
- **Advanced Analytics**: More detailed performance insights
- **Custom Model Training**: User-specific model fine-tuning

### Performance Improvements
- **GPU Acceleration**: Enhanced GPU utilization for faster processing
- **Caching System**: Intelligent caching for improved response times
- **Load Balancing**: Advanced request distribution
- **Compression Optimization**: Better file size and quality balance

---

**Built with excellence for the Building Bots Network** 🌟

*This service embodies the network's mission of construction excellence, providing production-ready video generation capabilities with intelligent optimization and seamless integration.*