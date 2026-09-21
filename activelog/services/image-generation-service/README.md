# Comprehensive Image Generation Service

A production-ready, AI-powered image generation service that extends the existing DALL-E 3 integration with advanced features including Stable Diffusion support, intelligent style detection, ML-powered prompt optimization, batch processing, and user preference learning.

## 🌟 Key Features

### Core Generation Capabilities
- **DALL-E 3 Integration**: High-quality image generation via existing OpenAI service
- **Stable Diffusion Support**: Local generation with customizable parameters
- **Intelligent Model Selection**: Automatic model recommendation based on prompt analysis
- **Multiple Format Support**: PNG, JPEG, WebP, BMP output formats
- **Flexible Sizing**: Support for various image dimensions up to 2048x2048

### Advanced AI Features
- **Style Detection**: Automatically identifies image style from prompts
- **Prompt Enhancement**: ML-powered prompt optimization for better results
- **Quality Prediction**: Intelligent quality scoring and prediction
- **User Learning**: Personalized recommendations based on user preferences
- **Batch Processing**: Efficient generation of multiple images

### Image Editing & Enhancement
- **Image Enhancement**: Brightness, contrast, saturation, sharpness adjustments
- **Upscaling**: AI-powered image upscaling with multiple algorithms
- **Style Transfer**: Apply artistic styles to existing images
- **Inpainting/Outpainting**: Fill or extend image content (placeholder for future ML models)

### Production Features
- **Cost Optimization**: Intelligent cost management and tracking
- **Performance Monitoring**: Comprehensive analytics and insights
- **Rate Limiting**: Configurable request limits and throttling
- **Error Handling**: Robust error recovery and logging
- **Hub Integration**: Seamless integration with Generative Tools Hub

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Access to OpenAI Integration Service (localhost:8475)
- Optional: Generative Tools Hub (localhost:8500)
- Optional: Local AI Service (localhost:8471)

### Installation

1. **Clone/Navigate to the service directory**
   ```bash
   cd /home/activeloguser/activelog/services/image-generation-service/
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the service**
   ```bash
   ./start_service.sh
   ```

   Or manually:
   ```bash
   python main.py
   ```

The service will start on `http://localhost:8480` by default.

### Environment Variables

Set these environment variables to customize the service:

```bash
export IMG_GEN_SERVICE_PORT=8480
export IMG_GEN_DEBUG_MODE=false
export IMG_GEN_DATABASE_PATH="./image_generation.db"
export IMG_GEN_ENABLE_HUB_INTEGRATION=true
export IMG_GEN_MAX_BATCH_SIZE=20
export IMG_GEN_DAILY_COST_LIMIT_USD=50.0
```

## 📖 API Documentation

### Core Endpoints

#### Generate Single Image
```bash
POST /generate
```

**Request Body:**
```json
{
  "prompt": "A futuristic cityscape at sunset, cyberpunk style",
  "user_id": "user123",
  "style": "sci_fi",
  "quality": "high",
  "size": "1024x1024",
  "format": "png",
  "enhance_prompt": true,
  "model_preference": "dall-e-3"
}
```

**Response:**
```json
{
  "success": true,
  "generation_id": "gen_abc123",
  "model_used": "dall-e-3",
  "original_prompt": "A futuristic cityscape at sunset, cyberpunk style",
  "enhanced_prompt": "A futuristic cityscape at sunset, cyberpunk style, highly detailed, professional quality, ultra-realistic",
  "detected_style": "sci_fi",
  "quality_score": 8.7,
  "generation_time": 12.5,
  "cost": 0.040,
  "image_url": "http://localhost:8480/generated/gen_abc123.png"
}
```

#### Batch Generation
```bash
POST /generate/batch
```

**Request Body:**
```json
{
  "prompts": [
    "Modern office interior",
    "Cozy coffee shop atmosphere", 
    "Minimalist bedroom design"
  ],
  "user_id": "user123",
  "base_style": "modern",
  "quality": "standard",
  "variations_per_prompt": 2
}
```

#### Style Analysis
```bash
POST /analyze/style
```

**Request Body:**
```json
{
  "prompt": "Watercolor painting of a forest",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "detected_styles": {
    "artistic": 0.9,
    "watercolor": 0.8,
    "natural": 0.6
  },
  "recommended_model": "stable-diffusion",
  "primary_style": "artistic",
  "confidence_scores": {
    "artistic": 0.9,
    "watercolor": 0.8
  }
}
```

#### Prompt Optimization
```bash
POST /optimize/prompt
```

**Request Body:**
```json
{
  "original_prompt": "Nice picture of a cat",
  "target_style": "photorealistic",
  "improvement_focus": "quality",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "original_prompt": "Nice picture of a cat",
  "optimized_prompt": "Nice picture of a cat, highly detailed, professional photography, sharp focus, DSLR quality",
  "improvements": [
    "Added quality booster: highly detailed",
    "Added photorealistic enhancer: professional photography"
  ],
  "enhancement_score": 0.8
}
```

#### Image Editing
```bash
POST /edit
```

Upload image file with form data:
- `image`: Image file
- `operation`: "enhance", "upscale", "style_transfer"
- `parameters`: JSON string with operation parameters

### Analytics Endpoints

#### User Analytics
```bash
GET /analytics/user/{user_id}
```

#### System Analytics  
```bash
GET /analytics/system
```

#### Service Health
```bash
GET /
```

### Learning and Feedback

#### Submit Feedback
```bash
POST /feedback
```

**Request Body:**
```json
{
  "image_id": "gen_abc123",
  "user_id": "user123", 
  "quality_score": 8.5,
  "style_accuracy": 9.0,
  "prompt_adherence": 8.0,
  "overall_satisfaction": 8.5,
  "comments": "Great quality, exactly what I wanted"
}
```

## 🎯 Style Detection

The service automatically detects image styles from prompts and recommends optimal models:

### Supported Styles
- **Photorealistic**: Professional photography, product shots
- **Artistic**: Paintings, fine art, creative works
- **Digital Art**: Digital illustrations, concept art, CGI
- **Anime**: Manga-style illustrations, character art
- **Sketch**: Line art, pencil drawings, wireframes
- **Vintage**: Retro, aged, classic styles
- **Modern**: Contemporary, minimalist, sleek designs
- **Fantasy**: Magical, mystical, surreal imagery
- **Sci-Fi**: Futuristic, cyberpunk, space themes
- **Abstract**: Geometric, conceptual, non-representational

### Model Recommendations
- **DALL-E 3**: Best for photorealistic, digital art, UI mockups, marketing visuals
- **Stable Diffusion**: Best for artistic, anime, sketches, fantasy, abstract art

## 🔧 Configuration

### Service Configuration

Edit `config.py` or use environment variables to customize:

```python
# Service settings
service_port = 8480
debug_mode = False

# Model settings  
enable_dall_e_3 = True
enable_stable_diffusion = True

# Features
enable_prompt_enhancement = True
enable_style_detection = True
enable_user_learning = True
enable_hub_integration = True

# Limits
max_batch_size = 20
daily_cost_limit_usd = None
requests_per_minute = 60
```

### Quality Levels

- **Draft** (0.5x cost): Quick iterations, concept sketches
- **Standard** (1.0x cost): General content, social media
- **High** (1.5x cost): Professional content, marketing
- **Professional** (2.0x cost): Premium content, print quality

### Model Configuration

Each model can be individually configured:

```python
"dall-e-3": {
    "enabled": True,
    "cost_per_image": 0.040,
    "max_concurrent": 3,
    "timeout_seconds": 120
}

"stable-diffusion": {
    "enabled": True,
    "local_model_path": "/models/stable-diffusion",
    "use_gpu": True,
    "inference_steps": 50
}
```

## 📊 Monitoring & Analytics

### User Analytics
- Generation history and preferences
- Style and model usage patterns  
- Quality scores and satisfaction ratings
- Cost tracking and optimization suggestions

### System Analytics
- Total generations and success rates
- Model performance comparisons
- Popular styles and trends
- Cost analysis and optimization insights

### Performance Monitoring
- Generation times and throughput
- Error rates and failure analysis
- Resource usage and optimization
- Real-time service health

## 🔗 Integration

### Generative Tools Hub Integration

The service automatically registers with the Generative Tools Hub if available:

```python
# Registration includes:
- Service capabilities and endpoints
- Supported models and styles  
- Quality tiers and cost structure
- Specialties and use cases

# Hub features:
- Intelligent model recommendations
- Cross-service preference learning
- Global trend analysis
- Enhanced generation with hub intelligence
```

### OpenAI Integration Service

Leverages the existing OpenAI integration at `localhost:8475` for:
- DALL-E 3 image generation
- Cost management and rate limiting
- User preference tracking
- Quality optimization

## 🧠 Machine Learning Features

### Prompt Enhancement
- **Quality Boosters**: Adds professional quality terms
- **Style Enhancers**: Style-specific improvement terms  
- **Specificity Improvements**: Adds detail for short prompts
- **Creativity Boosts**: Enhances creative and artistic prompts

### Style Classification
- **Keyword Analysis**: Identifies style from prompt keywords
- **Confidence Scoring**: Measures detection certainty
- **Model Mapping**: Recommends optimal model for each style
- **Use Case Analysis**: Suggests appropriate applications

### Quality Prediction
- **Multi-factor Analysis**: Considers prompt, style, model, parameters
- **User Feedback Integration**: Learns from satisfaction ratings
- **Continuous Improvement**: Updates predictions based on outcomes
- **Personalization**: Adapts to individual user preferences

### User Preference Learning
- **Exponential Moving Average**: Gradual learning from feedback
- **Style Preferences**: Learns preferred styles and models
- **Quality Preferences**: Adapts quality recommendations
- **Cost Optimization**: Balances quality with cost preferences

## 🛠️ Development

### Project Structure
```
image-generation-service/
├── main.py                 # Main FastAPI application
├── config.py              # Configuration management
├── hub_integration.py     # Generative hub integration
├── requirements.txt       # Python dependencies
├── start_service.sh      # Startup script
├── README.md             # This documentation
├── image_generation.db   # SQLite database
├── venv/                 # Virtual environment
└── logs/                 # Service logs
```

### Adding New Models

1. Update model configuration in `config.py`
2. Add generation method in `main.py`
3. Update style recommendations
4. Add model-specific parameters
5. Update documentation

### Adding New Styles

1. Add style keywords to `style_keywords` dict
2. Update style configuration
3. Add enhancement prompts
4. Update model recommendations
5. Test style detection accuracy

### Custom Enhancement Strategies

```python
# Add to prompt_enhancer configuration
"custom_style": {
    "enhancement_patterns": {
        "quality_boosters": ["custom quality terms"],
        "style_enhancers": ["style-specific terms"]
    }
}
```

## 🔒 Security & Best Practices

### API Security
- Optional API key authentication
- Rate limiting and request throttling
- Input validation and sanitization
- Error message sanitization

### Data Privacy
- User preference data encryption
- Secure database storage
- Optional data retention policies
- GDPR compliance considerations

### Cost Management
- Daily cost limits and alerts
- Per-user cost tracking
- Model cost optimization
- Automatic fallback to cheaper models

## 📈 Performance Optimization

### Generation Performance
- Concurrent generation limits
- Intelligent queuing and prioritization
- Resource usage monitoring
- Automatic scaling recommendations

### Caching Strategy
- Generated image caching
- Style analysis caching
- Prompt optimization caching
- User preference caching

### Database Optimization
- Indexed queries for analytics
- Automatic cleanup of old data
- Performance monitoring
- Query optimization suggestions

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start
- Check Python version (3.8+ required)
- Verify dependencies are installed
- Check port availability
- Review service logs

#### Generation Failures
- Verify OpenAI service connectivity
- Check API key configuration
- Monitor rate limits
- Review error logs

#### Poor Quality Results
- Enable prompt enhancement
- Try different quality levels
- Check style detection accuracy
- Provide user feedback for learning

#### High Costs
- Enable cost limits
- Use local models for appropriate content
- Monitor daily usage
- Optimize quality settings

### Debugging

Enable debug mode for detailed logging:
```bash
export IMG_GEN_DEBUG_MODE=true
export IMG_GEN_LOG_LEVEL=DEBUG
```

View service logs:
```bash
tail -f service.log
```

Check service health:
```bash
curl http://localhost:8480/
```

## 📋 Roadmap

### Upcoming Features
- [ ] Advanced Stable Diffusion model integration
- [ ] Real-time image editing with AI
- [ ] Video generation capabilities
- [ ] Advanced style transfer models
- [ ] Mobile app integration
- [ ] Enterprise SSO integration
- [ ] Advanced analytics dashboard
- [ ] Multi-language support

### Performance Improvements
- [ ] GPU optimization for local models
- [ ] Advanced caching strategies
- [ ] Distributed generation processing
- [ ] Real-time streaming results

## 🤝 Contributing

This service is part of the SuperInstance ecosystem. For improvements:

1. Test thoroughly with existing integrations
2. Follow existing code patterns and conventions
3. Update documentation and configuration
4. Ensure backward compatibility
5. Add appropriate logging and monitoring

## 📄 License

Part of the SuperInstance project ecosystem. See project license for details.

## 📞 Support

For issues or questions:
- Check service logs and health endpoints
- Review this documentation
- Test with minimal examples
- Monitor service analytics for insights

---

**Built with ❤️ for the SuperInstance ecosystem**

*Intelligent image generation with production-ready features and seamless integration.*