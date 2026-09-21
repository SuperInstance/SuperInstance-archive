# What's Next - Content Studio Setup

## Current Status

✓ **Code Complete**: All Python files created
✓ **Config Complete**: Bootcamp and bot configs ready
✓ **Docs Complete**: Full documentation created
⏳ **Pip Install**: Running in background (check with `tail -f /tmp/pip_install.log`)
❌ **Ollama**: Needs installation
❌ **Models**: Need to download after Ollama installed
❌ **API Key**: Needs to be added to `.env`

## Action Items (In Order)

### 1. Wait for Pip to Finish

Check if still running:
```bash
ps aux | grep "pip install"
```

Monitor progress:
```bash
tail -f /tmp/pip_install.log
```

When complete, verify:
```bash
source venv/bin/activate
python test_imports.py
```

### 2. Install Ollama

This requires sudo, so you'll need to enter your password:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start the service:
```bash
ollama serve > /tmp/ollama.log 2>&1 &
```

Verify:
```bash
curl http://localhost:11434/api/tags
# Should return: {"models":[]}
```

### 3. Start Model Downloads (In Background)

Run our automated script:
```bash
./download_models.sh
```

This starts downloading ~5.2GB in the background.

**Monitor progress:**
```bash
# Watch the download log
tail -f /tmp/ollama_downloads.log

# Check what's downloaded so far
ollama list
```

**Expected timeline** (with slow connection):
- llama3.2:1b (1.3GB) → 10-15 minutes
- llama3.2:3b (2.0GB) → 15-20 minutes
- qwen2.5-coder:3b (1.9GB) → 12-18 minutes
- **Total**: 40-50 minutes

### 4. Add Your Claude API Key (While Downloads Run)

Get your key:
1. Go to: https://console.anthropic.com/
2. Sign in
3. Go to "API Keys"
4. Create key named "Content Studio"
5. Copy it (starts with `sk-ant-...`)

Add to .env:
```bash
nano .env
# Change this line:
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# To your actual key:
ANTHROPIC_API_KEY=sk-ant-api03-abc123...
```

Save and exit (Ctrl+X, Y, Enter)

### 5. Run Configuration Tests

```bash
# Test configuration
python test_config.py

# Test Python imports
source venv/bin/activate
python test_imports.py
```

Both should show all ✓ green checks.

### 6. Wait for Models to Finish

Check if downloads complete:
```bash
ollama list
```

Should show all 3 models:
```
NAME                    ID              SIZE      MODIFIED
llama3.2:1b            abc123...       1.3 GB    X minutes ago
llama3.2:3b            def456...       2.0 GB    X minutes ago
qwen2.5-coder:3b       ghi789...       1.9 GB    X minutes ago
```

Test a model:
```bash
ollama run llama3.2:1b "Hello, test response"
```

### 7. Start the Content Studio!

```bash
./start.sh
```

You should see:
```
🚀 Initializing Loopless Content Studio...
📚 Content bootcamp file loaded
 ✓ Created script_writer_1 (script_writer)
 ✓ Created script_writer_2 (script_writer)
 ... (more bots)
✅ Content Studio initialized successfully!
📊 14 bots ready
🤖 Starting story_indexer_1 (story_indexer)
📚 Indexed: The Knock That Changes Everything
...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 8. Test the System

Open a new terminal and test:

```bash
# Check status
curl http://localhost:8000/api/status | jq

# Send a request
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all available stories",
    "user_id": "me"
  }' | jq
```

### 9. Create Your First Episode!

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Episode 1 for YouTube (28 minutes)",
    "user_id": "me"
  }' | jq
```

Watch the terminal where the server is running - you'll see:
- story_indexer_1 finding Story 1
- script_writer_1 adapting to script
- image_prompter_1 generating prompts
- dialogue_formatter_1 formatting dialogue
- qa_content_1 reviewing quality
- metadata_gen_1 creating YouTube metadata

## Timeline Summary

| Task | Time | Can Work Parallel? |
|------|------|-------------------|
| Pip install | 10-15 min | ✓ Running now |
| Ollama install | 2 min | After pip |
| Model downloads | 40-50 min | ✓ Run in background |
| Add API key | 2 min | ✓ While models download |
| Test & start | 5 min | After models |
| **Total** | **~60 min** | |

## What to Do While Waiting

### Read Documentation
- **START_HERE.md** - System architecture overview
- **COMMANDS.md** - All available commands
- **SETUP.md** - Detailed troubleshooting
- **BUILD_LOG.md** - How system was built

### Explore the Code
```bash
# Check out the bot implementations
cat src/bots/content_bots.py

# See the bootcamp (what Claude knows)
cat config/content_bootcamp.md

# Review bot configurations
cat config/content_bot_configs.yaml
```

### Plan Your Content
- Which stories to produce first?
- YouTube vs Podcast priority?
- Social media strategy?

## Quick Reference Commands

```bash
# Check pip install status
tail -f /tmp/pip_install.log

# Check model downloads
tail -f /tmp/ollama_downloads.log
ollama list

# Test configuration
python test_config.py

# Start system
./start.sh

# Check system status
curl http://localhost:8000/api/status

# Stop system
# Press Ctrl+C in terminal where it's running
```

## Troubleshooting

**Pip install taking forever?**
- Slow internet = slow downloads
- Large packages: grpcio (6.5MB), numpy (16.8MB), onnxruntime (17.4MB)
- Total ~100MB+ to download
- Can continue once it finishes

**Ollama won't start?**
- Check if already running: `ps aux | grep ollama`
- Check logs: `tail /tmp/ollama.log`
- Try: `killall ollama && ollama serve &`

**Models downloading slow?**
- This is normal with slow connection
- Can continue working on code while they download
- System won't run without models though

**Can't connect to API?**
- Verify key in .env: `grep ANTHROPIC_API_KEY .env`
- Test key: https://console.anthropic.com/

## Success Criteria

You're ready when:
- [ ] `python test_imports.py` → All ✓
- [ ] `python test_config.py` → All ✓
- [ ] `ollama list` → Shows 3 models
- [ ] `./start.sh` → Server starts without errors
- [ ] `curl http://localhost:8000/api/status` → Returns JSON

Then you can start creating content! 🎬✨

---

**Estimated total setup time**: ~60 minutes (mostly waiting for downloads)
**Active work required**: ~10 minutes
