# Complete Setup Guide - Loopless Content Studio

This guide will walk you through setting up the multi-agent content creation system from scratch.

## Prerequisites

- Ubuntu/Debian Linux (WSL2 works great)
- Python 3.10+
- 16GB+ RAM recommended
- NVIDIA GPU with 8GB+ VRAM (your RTX 5090 is perfect!)
- Internet connection for downloading models

## Step 1: Install Ollama (Local LLM Runtime)

Ollama is required to run the local language models that power your bots.

### Installation

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

If you get a sudo password prompt, enter your password.

### Verify Installation

```bash
# Check Ollama is installed
ollama --version

# Start Ollama service (if not auto-started)
ollama serve &
```

You should see something like: `ollama version is 0.x.x`

## Step 2: Download Required Models

These models power your content creation bots. Download them in order (smallest to largest).

### Download Models

```bash
# Model 1: llama3.2:1b (~1.3GB)
# Used by: always-running bots (story_indexer, asset_monitor, etc.)
ollama pull llama3.2:1b

# Model 2: llama3.2:3b (~2.0GB)
# Used by: script_writer, image_prompter, qa_content
ollama pull llama3.2:3b

# Model 3: qwen2.5-coder:3b (~1.9GB)
# Used by: complex content generation (optional but recommended)
ollama pull qwen2.5-coder:3b
```

**Download times**:
- On good connection: ~10-15 minutes total
- On slower connection: ~30-45 minutes total

### Verify Models Downloaded

```bash
ollama list
```

You should see:
```
NAME                ID              SIZE      MODIFIED
llama3.2:1b        abc123...       1.3 GB    X minutes ago
llama3.2:3b        def456...       2.0 GB    X minutes ago
qwen2.5-coder:3b   ghi789...       1.9 GB    X minutes ago
```

## Step 3: Set Up Python Environment

### Create Virtual Environment

```bash
cd /home/activeloguser/content-studio-dev

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Verify activation (you should see (venv) in your prompt)
which python
```

### Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies (this will take 5-10 minutes)
pip install -r requirements.txt
```

**What's being installed**:
- FastAPI - Web server
- Anthropic - Claude API
- Ollama - Local LLM interface
- ChromaDB - Vector database
- PyTorch - ML framework (large download)
- Plus 20+ other packages

### Verify Installation

```bash
# Check key packages
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import anthropic; print('Anthropic:', anthropic.__version__)"
python -c "import ollama; print('Ollama OK')"
python -c "import chromadb; print('ChromaDB OK')"
```

All should print version numbers or "OK" with no errors.

## Step 4: Configure Environment Variables

### Get Your Claude API Key

1. Go to: https://console.anthropic.com/
2. Sign in or create account
3. Go to "API Keys"
4. Create a new key (name it "Content Studio")
5. Copy the key (starts with `sk-ant-...`)

### Create .env File

```bash
cd /home/activeloguser/content-studio-dev

# Copy example file
cp .env.example .env

# Edit with your API key
nano .env
```

**Edit these lines in .env**:
```bash
# Replace with your actual API key
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# Leave these as-is (default values)
OLLAMA_URL=http://localhost:11434
STORY_SOURCE_PATH=/home/activeloguser
STORY_PATTERN=Story_*_v3.md
```

Save and exit (Ctrl+X, then Y, then Enter)

### Verify .env File

```bash
# Check API key is set (won't show actual key for security)
grep ANTHROPIC_API_KEY .env
```

Should show: `ANTHROPIC_API_KEY=sk-ant-...`

## Step 5: Initialize Data Directories

```bash
cd /home/activeloguser/content-studio-dev

# Create all required directories
mkdir -p data/knowledge_base/chroma
mkdir -p data/loras/user_preferences
mkdir -p data/loras/project_specific
mkdir -p data/assets/characters
mkdir -p data/assets/backgrounds
mkdir -p data/assets/audio
mkdir -p data/assets/video
mkdir -p data/output/youtube
mkdir -p data/output/podcast
mkdir -p data/output/social
mkdir -p logs

# Verify structure
tree data -L 2
```

## Step 6: Verify Story Files

Your system needs to find your 60 story files.

```bash
# Count story files
ls ~/Story_*_v3.md 2>/dev/null | wc -l
```

Should show: `60`

If it shows `0`, check where your story files are located:
```bash
find ~ -name "Story_*_v3.md" -type f | head -5
```

If they're in a different location, update `STORY_SOURCE_PATH` in `.env`

## Step 7: Test Ollama Connection

```bash
# Make sure Ollama is running
ps aux | grep ollama

# If not running, start it
ollama serve &

# Wait 3 seconds, then test
sleep 3
curl http://localhost:11434/api/tags
```

Should return JSON with your downloaded models.

## Step 8: Start the Content Studio

### First Time Startup

```bash
cd /home/activeloguser/content-studio-dev

# Make sure venv is activated
source venv/bin/activate

# Start the system
python -m src.orchestrator.main
```

**What you should see**:
```
🚀 Initializing Loopless Content Studio...
📚 Content bootcamp file loaded
 ✓ Created script_writer_1 (script_writer)
 ✓ Created script_writer_2 (script_writer)
 ✓ Created image_prompter_1 (image_prompt)
 ✓ Created dialogue_formatter_1 (dialogue)
 ✓ Created story_indexer_1 (story_indexer)
 ✓ Created asset_monitor_1 (asset_monitor)
 ... more bots ...
✅ Content Studio initialized successfully!
📊 14 bots ready
🤖 Starting script_writer_1 (script_writer)
🤖 Starting script_writer_2 (script_writer)
... more bot starts ...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Watch for**:
- All bots starting (🤖)
- Story indexer finding your stories (📚)
- Server ready on port 8000

### If You See Errors

**"ModuleNotFoundError"**:
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**"Connection refused to Ollama"**:
```bash
# Start Ollama in another terminal
ollama serve
```

**"ANTHROPIC_API_KEY not set"**:
```bash
# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Export it manually
export ANTHROPIC_API_KEY="your-key-here"
```

## Step 9: Test the System

Open a **NEW terminal** (keep the server running in the first one).

### Test 1: Check Status

```bash
curl http://localhost:8000/api/status | jq
```

Should show JSON with all bot statuses.

### Test 2: Simple Request

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all available stories",
    "user_id": "test"
  }' | jq
```

### Test 3: Episode Creation

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Episode 1 for YouTube (28 minutes)",
    "user_id": "test"
  }' | jq
```

**What happens**:
1. Claude analyzes your request
2. Breaks it into tasks
3. Assigns to appropriate bots
4. Bots execute in parallel
5. Returns progress update

Watch the server terminal for bot activity:
```
📋 Assigned task abc-123 to script_writer_1
📋 Assigned task def-456 to image_prompter_1
✅ Task completed by script_writer_1
```

## Step 10: Monitor with WebSocket (Optional)

You can monitor in real-time using WebSocket.

Create a test file `test_websocket.py`:

```python
import asyncio
import websockets
import json

async def monitor():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        print("Connected to Content Studio!")
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"\n=== Update at {data['timestamp']} ===")
            active = [b for b, info in data['bots'].items()
                     if info['status'] == 'working']
            print(f"Active bots: {', '.join(active) if active else 'None'}")
            print(f"Queue: {data['queue']}")

asyncio.run(monitor())
```

Run it:
```bash
python test_websocket.py
```

## Troubleshooting Guide

### Models Not Downloading

**Error**: "Connection refused" or timeout
**Fix**:
```bash
# Check internet connection
ping -c 3 ollama.com

# Try different model server (if in China/restricted region)
export OLLAMA_HOST=0.0.0.0:11434
```

### GPU Not Being Used

**Check GPU**:
```bash
nvidia-smi
```

**Enable GPU for Ollama**:
```bash
# Ollama should auto-detect GPU
# Verify with:
ollama run llama3.2:1b "test" --verbose
# Should show GPU being used
```

### High Memory Usage

If system uses too much RAM:

**Edit** `config/content_bot_configs.yaml`:
```yaml
system:
  max_parallel_bots: 3  # Reduce from 6
```

### Bots Not Responding

**Check Ollama**:
```bash
# Test directly
ollama run llama3.2:1b "Hello, test"
```

**Check Bot Logs**:
```bash
# Watch server output for errors
# Look for 🆘 help requests
```

### Story Indexer Not Finding Files

**Check path**:
```bash
# What's configured
grep STORY_SOURCE_PATH .env

# What exists
ls -la ~/Story_*_v3.md | head -5
```

**Update path** in `.env` if needed.

## Quick Reference Commands

### Start System
```bash
cd /home/activeloguser/content-studio-dev
source venv/bin/activate
python -m src.orchestrator.main
```

### Stop System
Press `Ctrl+C` in the server terminal

### Check Status
```bash
curl http://localhost:8000/api/status
```

### View Logs
```bash
# Server logs in terminal where you started it
# Or redirect to file:
python -m src.orchestrator.main > logs/server.log 2>&1
```

### Restart After Changes
```bash
# Ctrl+C to stop
# Then restart:
python -m src.orchestrator.main
```

## What's Next?

Once setup is complete:

1. **Test Episode 1 creation** - Full workflow test
2. **Review generated script** - Check quality
3. **Adjust bot configs** - Tune temperature, tokens
4. **Add more bots** - Scale up parallel processing
5. **Integrate external tools** - Connect image_generator.py

## Performance Expectations

**With RTX 5090**:
- Bot response time: 2-5 seconds
- Parallel bots: 6-8 simultaneously
- Episode script: 3-5 minutes
- Full episode workflow: 15-20 minutes

**Cost per episode**:
- Local processing: FREE
- Claude API: $1-3
- Total: <$5 per episode

## Getting Help

If you encounter issues:

1. **Check logs** - Look for error messages
2. **Check this guide** - Review troubleshooting section
3. **Test components** - Isolate what's failing
4. **Check configs** - Verify .env and YAML files

## Success Checklist

Before considering setup complete, verify:

- [ ] Ollama installed and running
- [ ] All 3 models downloaded (llama3.2:1b, 3b, qwen2.5-coder:3b)
- [ ] Python dependencies installed
- [ ] .env file created with API key
- [ ] Server starts without errors
- [ ] All 14 bots initialize
- [ ] Story indexer finds 60 stories
- [ ] Status endpoint returns JSON
- [ ] Simple request works
- [ ] Can assign tasks to bots

Once all checked ✓, you're ready to produce content!
