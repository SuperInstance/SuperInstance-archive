# Video Processor Service

Advanced video processing and analysis service for the ActiveLog platform.

## Features

- **Keyframe Extraction**: Extract significant frames using multiple algorithms (interval, difference, optical flow, visual features)
- **Thumbnail Generation**: Generate poster thumbnails, timeline thumbnails, and preview videos
- **Scene Detection**: Detect scene boundaries using histogram, optical flow, content-aware, and audio-based methods
- **OCR Processing**: Extract text from video frames using Tesseract with multiple preprocessing techniques
- **AI Summaries**: Generate comprehensive video summaries using OpenAI, Anthropic, or local AI models
- **Subtitle Processing**: Extract embedded subtitles, find external subtitle files, and index content
- **Streaming Support**: Real-time video processing for live streams with WebSocket updates

## Installation

1. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg tesseract-ocr postgresql-client

# macOS
brew install ffmpeg tesseract postgresql
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/activelog"
export SERVICE_PORT=8007
export OPENAI_API_KEY="your_openai_key"  # Optional
export ANTHROPIC_API_KEY="your_anthropic_key"  # Optional
```

## Running the Service

### Development
```bash
python run.py
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8007 --workers 4
```

## API Endpoints

### Video Processing
- `POST /videos/upload` - Upload a video file
- `POST /videos/{job_id}/process` - Start video processing
- `GET /jobs/{job_id}/status` - Get processing status
- `GET /jobs/{job_id}/results` - Get processing results

### Search
- `POST /search` - Search videos by text, summaries, or subtitles

### Streaming
- `POST /streaming/sessions` - Start streaming processing session
- `DELETE /streaming/sessions/{session_id}` - Stop streaming session
- `GET /streaming/sessions` - List active sessions
- `WS /streaming/sessions/{session_id}/ws` - WebSocket for real-time updates

### Utilities
- `GET /health` - Health check
- `GET /statistics` - Processing statistics

## Usage Examples

### Upload and Process Video
```python
import requests

# Upload video
with open('video.mp4', 'rb') as f:
    response = requests.post('http://localhost:8007/videos/upload', files={'file': f})
job_id = response.json()['job_id']

# Start processing
requests.post(f'http://localhost:8007/videos/{job_id}/process', json={
    'extract_keyframes': True,
    'generate_thumbnails': True,
    'detect_scenes': True,
    'extract_text': True,
    'generate_summaries': True,
    'extract_subtitles': True
})
```

### Search Videos
```python
response = requests.post('http://localhost:8007/search', json={
    'query': 'presentation slides',
    'search_type': 'text',
    'limit': 10
})
```

## Dependencies

- Python 3.8+
- FFmpeg
- Tesseract OCR
- PostgreSQL 12+