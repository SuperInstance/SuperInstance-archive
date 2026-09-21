# Quick Command Reference

## Initial Setup (One Time)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download models (takes 10-15 minutes)
ollama pull llama3.2:1b    # 1.3GB
ollama pull llama3.2:3b    # 2.0GB
ollama pull qwen2.5-coder:3b  # 1.9GB

# 3. Verify models downloaded
ollama list

# 4. Edit .env file with your API key
nano .env
# Change: ANTHROPIC_API_KEY=your_anthropic_api_key_here
# Get key from: https://console.anthropic.com/

# 5. Verify Python dependencies installed
source venv/bin/activate
pip list | grep -E "fastapi|anthropic|ollama|chromadb"
```

## Daily Operations

### Start the System

```bash
# Easy way (checks everything)
./start.sh

# Manual way
source venv/bin/activate
python -m src.orchestrator.main
```

### Stop the System

```
Press Ctrl+C in the terminal
```

### Check System Status

```bash
# In a new terminal while server is running
curl http://localhost:8000/api/status | jq
```

### Send a Request

```bash
# Simple request
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all available stories",
    "user_id": "me"
  }' | jq

# Create Episode 1
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Episode 1 for YouTube (28 minutes)",
    "user_id": "me"
  }' | jq
```

## Testing

### Test Ollama Connection

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test a model directly
ollama run llama3.2:1b "Hello, test response"
```

### Test Claude API

```bash
# Set your API key if not in .env
export ANTHROPIC_API_KEY="your-key-here"

# Test with Python
python3 << EOF
import anthropic
client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hello"}]
)
print(message.content[0].text)
EOF
```

### Check Story Files

```bash
# Count your story files
ls ~/Story_*_v3.md | wc -l

# List first 5
ls ~/Story_*_v3.md | head -5

# If in different location, find them
find ~ -name "Story_*_v3.md" -type f
```

## Troubleshooting

### Ollama Not Running

```bash
# Start Ollama
ollama serve &

# Or in foreground (to see logs)
ollama serve
```

### Models Not Downloaded

```bash
# See what you have
ollama list

# Download missing models
ollama pull llama3.2:1b
ollama pull llama3.2:3b
```

### Python Package Issues

```bash
# Reinstall all packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-minimal.txt --force-reinstall
```

### API Key Not Working

```bash
# Check if it's set
echo $ANTHROPIC_API_KEY

# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Set manually
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### Port Already in Use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill it
kill $(lsof -t -i:8000)

# Or use different port
python -m uvicorn src.orchestrator.main:app --port 8001
```

## Monitoring

### View Logs

```bash
# Server logs (in terminal where you started it)
# Or redirect to file:
python -m src.orchestrator.main > logs/server.log 2>&1

# View log file
tail -f logs/server.log
```

### Watch GPU Usage (RTX 5090)

```bash
# Install nvidia-smi if not available
nvidia-smi

# Watch in real-time
watch -n 1 nvidia-smi
```

### Monitor System Resources

```bash
# CPU and Memory
htop

# Just memory
free -h

# Disk usage
df -h
```

## Development

### Edit Bot Configs

```bash
nano config/content_bot_configs.yaml
# Change: max_tokens, temperature, models, etc.
# Restart server after changes
```

### Edit Bootcamp (Claude's Context)

```bash
nano config/content_bootcamp.md
# Modify system instructions
# Restart server after changes
```

### Add New Bot

1. Edit `config/content_bot_configs.yaml`
2. Create bot class in `src/bots/content_bots.py`
3. Update `src/orchestrator/main.py` bot_classes dict
4. Restart server

### Test Individual Bot

```python
# Create test file: test_bot.py
import asyncio
from src.bots.content_bots import ScriptWriterBot
from src.bots.base_bot import BotConfig
from src.communication.help_queue import HelpQueue
from src.communication.message_bus import MessageBus
from src.knowledge.knowledge_base import KnowledgeBase

async def test():
    config = BotConfig(
        bot_id="test_script_writer",
        bot_type="script_writer",
        model="llama3.2:3b",
        specialty="Testing"
    )

    bot = ScriptWriterBot(
        config,
        HelpQueue(),
        MessageBus(),
        KnowledgeBase()
    )

    task = {
        "task_id": "test123",
        "description": "Test task",
        "story_content": "Once upon a time...",
        "format": "youtube_episode",
        "duration_minutes": 28
    }

    result = await bot.execute_task(task)
    print(result)

asyncio.run(test())
```

## Useful File Locations

```
content-studio-dev/
├── config/
│   ├── content_bootcamp.md         # Edit Claude's understanding
│   └── content_bot_configs.yaml    # Edit bot settings
├── src/
│   ├── orchestrator/main.py        # Main server
│   ├── bots/content_bots.py        # Bot implementations
│   └── bots/base_bot.py            # Bot foundation
├── .env                            # Your API keys
├── start.sh                        # Easy startup
├── SETUP.md                        # Full setup guide
└── COMMANDS.md                     # This file
```

## Getting Help

### Check Documentation

```bash
# Read in terminal
cat SETUP.md
cat START_HERE.md
cat BUILD_LOG.md
```

### Check Logs for Errors

```bash
# Look for error messages
grep -i error logs/server.log

# Look for help requests
grep "🆘" logs/server.log
```

### Reset Everything

```bash
# Stop server (Ctrl+C)

# Remove generated data
rm -rf data/knowledge_base/*
rm -rf data/loras/*

# Restart
./start.sh
```

## Common Tasks

### Create YouTube Episode

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{"message": "Create Episode 5 for YouTube", "user_id": "me"}' | jq
```

### Create Podcast Episode

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{"message": "Create Episode 3 for podcast format", "user_id": "me"}' | jq
```

### Generate Image Prompts Only

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate image prompts for Story 10 scenes 1-5", "user_id": "me"}' | jq
```

### Review Quality

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{"message": "Review quality of Episode 1 script", "user_id": "me"}' | jq
```

## Keyboard Shortcuts

While server is running:
- `Ctrl+C` - Stop server
- `Ctrl+Z` - Suspend (use `fg` to resume)

In terminal:
- `Ctrl+L` - Clear screen
- `Ctrl+R` - Search command history
- `Ctrl+A` - Move to start of line
- `Ctrl+E` - Move to end of line

## Next Steps

1. **Start the system**: `./start.sh`
2. **Test status**: `curl http://localhost:8000/api/status`
3. **Create Episode 1**: See "Create YouTube Episode" above
4. **Monitor logs**: Watch terminal for bot activity
5. **Review output**: Check what bots produced

Happy creating! 🎬✨
