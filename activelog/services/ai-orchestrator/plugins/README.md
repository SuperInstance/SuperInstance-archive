# AI Plugins for ActiveLog AI Orchestrator

Comprehensive AI integration plugins providing both cloud and local AI capabilities including text embeddings, content analysis, auto-tagging, image understanding, image generation, and local LLM support.

## Available Plugins

### 🌐 OpenAI Plugin
Cloud-based AI services with enterprise-grade capabilities.

### 🏠 Ollama Plugin  
Local LLM integration for privacy-focused and offline AI capabilities.

### 🎙️ Whisper Plugin
Audio transcription and searchable transcript management with Elasticsearch storage.

---

## OpenAI Plugin Features

### 🔤 Text Embeddings
- Uses OpenAI's `text-embedding-ada-002` model
- Generates 1536-dimensional embeddings
- Supports caching for performance
- Returns detailed metadata including token usage

### 🧠 Content Analysis & Tagging
- GPT-4 powered content analysis
- Multiple analysis types: general, sentiment, summary, topics, quality
- Automatic tag generation from content
- Custom analysis prompts support
- Configurable temperature and max tokens

### 🖼️ Image Understanding
- GPT-4 Vision integration for image analysis
- Multiple analysis types: description, objects, text extraction, scene analysis
- Support for different detail levels (low, high, auto)
- Base64 image input support

### 🎨 Image Generation
- DALL-E 3 integration
- Multiple sizes: 1024x1024, 1792x1024, 1024x1792
- Quality options: standard, hd
- Style options: vivid, natural
- Prompt revision tracking

### ⚡ Performance Features
- Redis-based response caching
- Configurable cache TTL
- Rate limiting with sliding windows
- Comprehensive error handling
- Request/response metrics tracking

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | ✅ |
| `OPENAI_TEXT_MODEL` | Text generation model | `gpt-4` | ❌ |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-ada-002` | ❌ |
| `OPENAI_VISION_MODEL` | Vision model | `gpt-4-vision-preview` | ❌ |
| `OPENAI_DALLE_MODEL` | Image generation model | `dall-e-3` | ❌ |
| `OPENAI_MAX_TOKENS` | Maximum tokens for generation | `4000` | ❌ |
| `OPENAI_TEMPERATURE` | Temperature for generation | `0.7` | ❌ |
| `OPENAI_TIMEOUT` | Request timeout (seconds) | `30` | ❌ |
| `OPENAI_ENABLE_CACHING` | Enable Redis caching | `true` | ❌ |
| `OPENAI_CACHE_TTL` | Cache TTL (seconds) | `3600` | ❌ |
| `OPENAI_RATE_LIMIT_RPM` | Requests per minute | `60` | ❌ |
| `OPENAI_RATE_LIMIT_TPM` | Tokens per minute | `150000` | ❌ |
| `OPENAI_RATE_LIMIT_RPD` | Requests per day | `5000` | ❌ |

### Setup Instructions

1. **Get OpenAI API Key**
   ```bash
   # Get your API key from https://platform.openai.com/api-keys
   export OPENAI_API_KEY='your-api-key-here'
   ```

2. **Optional Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit with your preferences
   nano .env
   ```

3. **Test the Plugin**
   ```bash
   python3 test_openai_plugin.py
   ```

## API Endpoints

### Text Embeddings
```http
POST /ai/embeddings
Content-Type: application/json

{
  "text": "Your text content here",
  "model": "text-embedding-ada-002"  // optional
}
```

### Content Analysis
```http
POST /ai/analyze
Content-Type: application/json

{
  "content": "Your content here",
  "analysis_type": "general",  // general, sentiment, summary, topics, quality
  "custom_prompt": "Custom analysis prompt"  // optional
}
```

### Tag Generation
```http
POST /ai/tags
Content-Type: application/json

{
  "content": "Your content here",
  "max_tags": 10  // optional, default 10
}
```

### Image Analysis
```http
POST /ai/analyze/image
Content-Type: application/json

{
  "image_data": "base64_encoded_image",
  "analysis_type": "description",  // description, objects, text, scene, style, emotions, technical
  "detail_level": "auto"  // low, high, auto
}
```

### Image Generation
```http
POST /ai/generate/image
Content-Type: application/json

{
  "prompt": "A beautiful sunset over mountains",
  "size": "1024x1024",      // 1024x1024, 1792x1024, 1024x1792
  "quality": "standard",    // standard, hd
  "style": "vivid"          // vivid, natural
}
```

### File Analysis (Upload)
```http
POST /analyze/file
Content-Type: multipart/form-data

file: [your file]
analysis_type: general  // optional
```

### Batch Analysis
```http
POST /batch/analyze
Content-Type: application/json

{
  "items": [
    {"content": "Text content 1", "id": "item1"},
    {"image_data": "base64_image", "id": "item2"}
  ],
  "analysis_type": "general"
}
```

## Rate Limiting

The plugin implements comprehensive rate limiting:

- **Per-minute limits**: Configurable requests per minute
- **Per-day limits**: Configurable requests per day
- **Token limits**: Tracks token usage for cost control
- **Sliding windows**: Accurate rate limiting without burst issues
- **Redis-based**: Distributed rate limiting across instances
- **Fallback**: In-memory rate limiting when Redis unavailable

## Caching

Response caching improves performance and reduces costs:

- **Redis storage**: Distributed caching across instances
- **Configurable TTL**: Set cache expiration time
- **Smart keys**: Content-based cache keys for accuracy
- **Hit/miss tracking**: Monitor cache performance
- **Automatic cleanup**: TTL-based cache expiration

## Error Handling

Robust error handling for production use:

- **Rate limit errors**: Clear messages when limits exceeded
- **API errors**: Detailed OpenAI API error reporting
- **Network errors**: Timeout and connection handling
- **Validation errors**: Input validation with helpful messages
- **Graceful degradation**: Continues operation on Redis failures

## Monitoring & Statistics

Track plugin performance and usage:

```http
GET /plugins/stats
```

Returns:
- Request counts by operation type
- Error rates and types
- Cache hit/miss ratios
- Rate limiting status
- Token usage statistics

## Security Considerations

- **API Key Protection**: Never log or expose API keys
- **Input Validation**: All inputs validated before processing
- **Rate Limiting**: Prevents abuse and cost overruns
- **Error Sanitization**: Sensitive info removed from error messages
- **Timeout Protection**: Prevents hanging requests

## Development

### Testing
```bash
# Run basic functionality test
python3 test_openai_plugin.py

# Test with API key
export OPENAI_API_KEY='your-key'
python3 test_openai_plugin.py
```

### Plugin Architecture
- **Modular Design**: Easy to extend with new capabilities
- **Async/Await**: Full async support for performance
- **Type Hints**: Complete type annotations
- **Error Handling**: Comprehensive exception management
- **Logging**: Detailed logging for debugging

### Adding New Features
1. Add method to `OpenAIPlugin` class
2. Update capabilities list
3. Add corresponding endpoint in `main.py`
4. Update tests and documentation

## Troubleshooting

### Common Issues

1. **"API key not configured"**
   - Set `OPENAI_API_KEY` environment variable
   - Verify key is valid and has credits

2. **"Rate limit exceeded"**
   - Check your OpenAI usage dashboard
   - Adjust rate limiting configuration
   - Consider upgrading OpenAI plan

3. **"Redis connection failed"**
   - Plugin works with in-memory fallback
   - Check Redis server status
   - Verify Redis connection settings

4. **"Request timeout"**
   - Increase `OPENAI_TIMEOUT` setting
   - Check network connectivity
   - Verify OpenAI API status

---

## Ollama Plugin Features

### 🏠 Local LLM Support
- Connect to local Ollama instance (default: localhost:11434)
- Support for multiple models: llama2, mistral, codellama, etc.
- Privacy-focused: all processing happens locally
- No API keys required

### 💬 Chat & Text Generation
- Chat completion with conversation context
- Text generation with custom prompts
- Streaming responses for real-time output
- Configurable temperature and token limits

### 🧮 Local Embeddings
- Generate embeddings using local models
- No data sent to external services
- Suitable for sensitive content processing

### 🔧 Model Management
- List available models
- Pull new models from Ollama library
- Delete unused models
- Automatic model availability checking

### 🔄 Fallback Mechanism
- Automatic fallback to OpenAI when Ollama unavailable
- Configurable fallback behavior
- Seamless user experience during outages

### ⚡ Performance Features
- Redis-based response caching
- Rate limiting for resource management
- Comprehensive error handling
- Request/response metrics tracking

## Ollama Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OLLAMA_HOST` | Ollama server host | `localhost` | ❌ |
| `OLLAMA_PORT` | Ollama server port | `11434` | ❌ |
| `OLLAMA_DEFAULT_MODEL` | Default model to use | `llama2` | ❌ |
| `OLLAMA_TIMEOUT` | Request timeout (seconds) | `60` | ❌ |
| `OLLAMA_MAX_TOKENS` | Maximum tokens | `2048` | ❌ |
| `OLLAMA_TEMPERATURE` | Generation temperature | `0.7` | ❌ |
| `OLLAMA_ENABLE_CACHING` | Enable Redis caching | `true` | ❌ |
| `OLLAMA_CACHE_TTL` | Cache TTL (seconds) | `1800` | ❌ |
| `OLLAMA_RATE_LIMIT_RPM` | Requests per minute | `100` | ❌ |
| `OLLAMA_ENABLE_FALLBACK` | Enable fallback | `true` | ❌ |
| `OLLAMA_FALLBACK_TO_OPENAI` | Fallback to OpenAI | `true` | ❌ |

### Setup Instructions

1. **Install Ollama**
   ```bash
   # Install Ollama (https://ollama.ai)
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama Service**
   ```bash
   # Start Ollama server
   ollama serve
   ```

3. **Pull Models**
   ```bash
   # Pull popular models
   ollama pull llama2
   ollama pull mistral
   ollama pull codellama
   ```

4. **Test Connection**
   ```bash
   python3 test_ollama_plugin.py
   ```

## API Endpoints

### Ollama Endpoints

#### Chat Completion
```http
POST /ollama/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "model": "llama2",
  "stream": false
}
```

#### Text Generation
```http
POST /ollama/generate
Content-Type: application/json

{
  "prompt": "Explain quantum computing",
  "model": "llama2",
  "stream": false
}
```

#### Embeddings Generation
```http
POST /ollama/embeddings
Content-Type: application/json

{
  "text": "Your text here",
  "model": "llama2"
}
```

#### Model Management
```http
# List models
GET /ollama/models

# Pull model
POST /ollama/models/pull
Content-Type: application/json
{
  "model": "mistral"
}

# Delete model
DELETE /ollama/models/{model_name}
```

### OpenAI Endpoints (Legacy)

#### Text Embeddings
```http
POST /ai/embeddings
Content-Type: application/json

{
  "text": "Your text content here",
  "model": "text-embedding-ada-002"
}
```

#### Content Analysis
```http
POST /ai/analyze
Content-Type: application/json

{
  "content": "Your content here",
  "analysis_type": "general"
}
```

## Plugin Selection Strategy

### Use Ollama When:
- Privacy is a concern
- Processing sensitive data
- Want to avoid API costs
- Need offline capabilities
- Have sufficient local compute resources

### Use OpenAI When:
- Need best-in-class performance
- Require image generation (DALL-E)
- Want access to latest GPT models
- Have limited local compute
- Need specialized capabilities (vision, etc.)

### Fallback Strategy:
- Primary: Use Ollama for cost and privacy
- Fallback: Use OpenAI when Ollama unavailable
- Configure via `OLLAMA_ENABLE_FALLBACK=true`

## Troubleshooting

### Common Issues

1. **"Ollama connection failed"**
   - Check if Ollama is running: `ollama serve`
   - Verify connection: `curl http://localhost:11434/api/tags`
   - Check firewall settings

2. **"Model not found"**
   - List available models: `ollama list`
   - Pull required model: `ollama pull llama2`
   - Check model name spelling

3. **"Rate limit exceeded"**
   - Adjust `OLLAMA_RATE_LIMIT_RPM` setting
   - Check concurrent request load
   - Consider upgrading hardware

4. **"Fallback failed"**
   - Verify OpenAI API key is set
   - Check OpenAI service status
   - Review fallback configuration

---

## Whisper Plugin Features

### 🎙️ Audio Transcription
- OpenAI Whisper API integration for high-quality transcription
- Support for multiple audio formats: mp3, wav, m4a, flac, ogg, webm
- Automatic language detection or manual language specification
- Configurable response formats including timestamps and word-level timing

### 📊 Metadata Extraction
- Extract audio metadata: duration, bitrate, sample rate, channels
- Support for ID3 tags: title, artist, album, date, genre
- Compatible with multiple audio container formats
- Automatic file validation and format verification

### 🔍 Searchable Transcripts
- Store transcripts in Elasticsearch with full-text search
- Advanced search with filters: language, format, duration, date range
- Highlight matching text in search results
- Nested segment and word-level search capabilities

### ⏱️ Timestamp Alignment
- Word-level and segment-level timestamps
- Precise timing information for audio synchronization
- Support for subtitle generation and editing
- Confidence scores for transcription accuracy

### 💾 Elasticsearch Storage
- Structured transcript storage with rich metadata
- Automatic index creation and management
- Optimized search performance with custom analyzers
- Support for large-scale transcript collections

### ⚡ Performance Features
- Redis-based response caching for repeated requests
- Rate limiting to manage API usage and costs
- File size validation and format checking
- Comprehensive error handling and logging

## Whisper Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | ✅ |
| `WHISPER_MODEL` | Whisper model to use | `whisper-1` | ❌ |
| `WHISPER_MAX_FILE_SIZE` | Max file size in bytes | `25000000` | ❌ |
| `WHISPER_DEFAULT_LANGUAGE` | Default language | `auto` | ❌ |
| `WHISPER_RESPONSE_FORMAT` | Response format | `verbose_json` | ❌ |
| `WHISPER_ENABLE_CACHING` | Enable Redis caching | `true` | ❌ |
| `WHISPER_CACHE_TTL` | Cache TTL (seconds) | `86400` | ❌ |
| `WHISPER_RATE_LIMIT_RPM` | Requests per minute | `50` | ❌ |
| `ELASTICSEARCH_HOST` | Elasticsearch host | `localhost` | ❌ |
| `ELASTICSEARCH_PORT` | Elasticsearch port | `9200` | ❌ |
| `ELASTICSEARCH_USERNAME` | ES username | - | ❌ |
| `ELASTICSEARCH_PASSWORD` | ES password | - | ❌ |
| `WHISPER_ES_INDEX` | ES index name | `audio_transcripts` | ❌ |

### Setup Instructions

1. **Configure OpenAI API**
   ```bash
   # Set your OpenAI API key
   export OPENAI_API_KEY='your-openai-api-key'
   ```

2. **Install Elasticsearch**
   ```bash
   # Using Docker
   docker run -d --name elasticsearch \
     -p 9200:9200 -p 9300:9300 \
     -e "discovery.type=single-node" \
     -e "xpack.security.enabled=false" \
     elasticsearch:8.11.0
   ```

3. **Install Dependencies**
   ```bash
   pip install elasticsearch[async] mutagen aiofiles
   ```

4. **Test Configuration**
   ```bash
   python3 test_whisper_plugin.py
   ```

## API Endpoints

### Whisper Endpoints

#### Audio Transcription
```http
POST /whisper/transcribe
Content-Type: multipart/form-data

file: [audio file]
language: en  # optional
prompt: "Custom context"  # optional
response_format: verbose_json  # optional
timestamp_granularities: word,segment  # optional
```

#### Search Transcripts
```http
GET /whisper/search?q=search_term&limit=10&offset=0
Query Parameters:
- q: search query (required)
- limit: results per page (default: 10)
- offset: pagination offset (default: 0)
- language: filter by language
- format: filter by audio format
- duration_min: minimum duration in seconds
- duration_max: maximum duration in seconds
- date_from: filter from date (ISO format)
- date_to: filter to date (ISO format)
```

#### Get Transcript
```http
GET /whisper/transcript/{file_hash}
```

#### Delete Transcript
```http
DELETE /whisper/transcript/{file_hash}
```

## Audio Format Support

### Supported Formats
- **MP3**: MPEG Audio Layer 3
- **WAV**: Waveform Audio File Format
- **M4A**: MPEG-4 Audio
- **FLAC**: Free Lossless Audio Codec
- **OGG**: Ogg Vorbis
- **WEBM**: WebM Audio

### File Size Limits
- Default maximum: 25MB per file
- Configurable via `WHISPER_MAX_FILE_SIZE`
- Automatic validation before processing

### Metadata Support
- **ID3 Tags**: Title, Artist, Album, Date, Genre
- **Audio Properties**: Duration, Bitrate, Sample Rate, Channels
- **Format Information**: Container type, codec details

## Elasticsearch Schema

### Transcript Document Structure
```json
{
  "file_name": "audio.mp3",
  "file_hash": "sha256_hash",
  "file_size": 1048576,
  "duration": 120.5,
  "format": "mp3",
  "language": "en",
  "transcript_text": "Full transcript text...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.2,
      "text": "Segment text",
      "words": [
        {
          "word": "Hello",
          "start": 0.0,
          "end": 0.5,
          "probability": 0.99
        }
      ]
    }
  ],
  "metadata": {
    "title": "Audio Title",
    "artist": "Artist Name",
    "duration": 120.5
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Use Cases

### Content Management
- **Podcast Transcription**: Searchable podcast archives
- **Meeting Notes**: Automatic meeting transcription and search
- **Media Libraries**: Audio content cataloging and discovery

### Accessibility
- **Subtitle Generation**: Create subtitles from audio tracks
- **Content Analysis**: Extract insights from audio content
- **Language Processing**: Multi-language content support

### Integration
- **CMS Integration**: Embed in content management systems
- **Workflow Automation**: Automated transcription pipelines
- **API Integration**: RESTful API for external applications

## Troubleshooting

### Common Issues

1. **"OpenAI API key not configured"**
   - Set `OPENAI_API_KEY` environment variable
   - Verify API key is valid and has credits
   - Check OpenAI account status

2. **"Elasticsearch connection failed"**
   - Verify Elasticsearch is running on specified host/port
   - Check network connectivity and firewall settings
   - Verify credentials if authentication is enabled

3. **"Unsupported format"**
   - Check file extension is in supported formats list
   - Verify file is not corrupted or empty
   - Convert to supported format if necessary

4. **"File size exceeds maximum"**
   - Check file size against `WHISPER_MAX_FILE_SIZE` limit
   - Compress audio file or split into smaller segments
   - Adjust configuration limit if appropriate

5. **"Rate limit exceeded"**
   - Check OpenAI API usage dashboard
   - Adjust `WHISPER_RATE_LIMIT_RPM` setting
   - Consider upgrading OpenAI plan

### Support

- Check logs for detailed error messages
- Monitor `/health` endpoint for system status
- Use `/plugins/stats` for usage analytics
- Test individual plugins with provided test scripts