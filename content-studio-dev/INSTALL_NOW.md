# Install & Run - Content Studio

**Current Status**: ✅ 80% Complete - All code working!

You need to complete **3 manual steps** (requires sudo password):

---

## Step 1: Install Ollama (2 minutes)

Ollama requires sudo privileges, so you'll need to enter your password:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**What you'll see:**
```
>>> Installing ollama to /usr/local
>>> Creating ollama user...
>>> Adding current user to ollama group...
>>> Creating ollama systemd service...
>>> Enabling and starting ollama service...
>>> Done!
```

**Verify installation:**
```bash
ollama --version
# Should show: ollama version is 0.x.x
```

---

## Step 2: Start Ollama Service

```bash
# Start Ollama in background
ollama serve > /tmp/ollama.log 2>&1 &

# Wait 3 seconds for it to initialize
sleep 3

# Verify it's running
curl http://localhost:11434/api/tags
# Should return: {"models":[]}
```

---

## Step 3: Download Models (40-50 minutes)

**IMPORTANT**: This runs in the background! You can continue working.

```bash
cd /home/activeloguser/content-studio-dev
./download_models.sh
```

This will download 3 models (~5.2GB total):
- llama3.2:1b (1.3GB) - 10-15 min
- llama3.2:3b (2.0GB) - 15-20 min
- qwen2.5-coder:3b (1.9GB) - 12-18 min

**Monitor progress:**
```bash
# Watch the download log
tail -f /tmp/ollama_downloads.log

# Check what's downloaded so far
ollama list
```

**While downloads run**, proceed to Step 4...

---

## Step 4: Add Your Claude API Key

Get your API key:
1. Go to: **https://console.anthropic.com/**
2. Sign in
3. Click "API Keys"
4. Create key named "Content Studio"
5. Copy it (starts with `sk-ant-...`)

Add to .env:
```bash
nano .env
```

Change this line:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

To your actual key:
```
ANTHROPIC_API_KEY=sk-ant-api03-abc123def456...
```

Save: `Ctrl+X`, then `Y`, then `Enter`

---

## Step 5: Wait for Models to Finish

Check if all models are downloaded:
```bash
ollama list
```

Should show all 3:
```
NAME                    ID              SIZE      MODIFIED
llama3.2:1b            abc123...       1.3 GB    X minutes ago
llama3.2:3b            def456...       2.0 GB    X minutes ago
qwen2.5-coder:3b       ghi789...       1.9 GB    X minutes ago
```

Test a model works:
```bash
ollama run llama3.2:1b "Hello, test"
# Should respond with a greeting
```

---

## Step 6: Start the Content Studio! 🚀

```bash
./start.sh
```

**You should see:**
```
╔════════════════════════════════════════╗
║  Loopless Content Studio Startup      ║
╚════════════════════════════════════════╝

→ Activating virtual environment...
→ Checking Ollama...
✓ Ollama is running
✓ llama3.2:1b ready
✓ llama3.2:3b ready

╔════════════════════════════════════════╗
║  Starting Content Studio...           ║
╚════════════════════════════════════════╝

Server will start on: http://localhost:8000
Press Ctrl+C to stop

🚀 Initializing Loopless Content Studio...
📚 Content bootcamp file loaded
 ✓ Created script_writer_1 (script_writer)
 ✓ Created script_writer_2 (script_writer)
 ✓ Created image_prompter_1 (image_prompt)
 ✓ Created dialogue_formatter_1 (dialogue)
 ✓ Created story_indexer_1 (story_indexer)
 ✓ Created asset_monitor_1 (asset_monitor)
 ... (more bots)
✅ Content Studio initialized successfully!
📊 14 bots ready
🤖 Starting story_indexer_1...
📚 Indexed: The Knock That Changes Everything
...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Step 7: Test the System

Open a **new terminal** and run:

```bash
# Test status
curl http://localhost:8000/api/status | jq
```

Should return JSON showing all bots and their status.

---

## Step 8: Create Your First Episode! 🎬

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Episode 1 for YouTube (28 minutes)",
    "user_id": "me"
  }' | jq
```

**Watch the terminal** where the server is running. You'll see:
- 📚 story_indexer_1 finding Story 1
- 📝 script_writer_1 adapting to script
- 🎨 image_prompter_1 generating prompts
- 🎤 dialogue_formatter_1 formatting dialogue
- ✅ qa_content_1 reviewing quality
- 📺 metadata_gen_1 creating YouTube metadata

---

## Timeline

| Step | Time | Can Do Parallel? |
|------|------|------------------|
| Install Ollama | 2 min | No (needs your password) |
| Start Ollama | 30 sec | No |
| Download models | 40-50 min | **✓ Yes - runs in background!** |
| Add API key | 2 min | **✓ Yes - while models download** |
| Start system | 1 min | After models finish |
| Test system | 2 min | After startup |
| **TOTAL** | **~50 min** | *But only ~5 min of your time!* |

---

## Quick Commands

```bash
# Check if Ollama is running
ps aux | grep ollama

# Check model download progress
tail -f /tmp/ollama_downloads.log

# Check what models are downloaded
ollama list

# Test a model
ollama run llama3.2:1b "test"

# Start content studio
./start.sh

# Check system status
curl http://localhost:8000/api/status

# Stop system
# Press Ctrl+C in terminal where it's running
```

---

## Troubleshooting

**"Ollama command not found"**
```bash
# Check if installed
which ollama

# If not found, re-run installer
curl -fsSL https://ollama.com/install.sh | sh
```

**"Connection refused to Ollama"**
```bash
# Start Ollama service
ollama serve &
sleep 3
curl http://localhost:11434/api/tags
```

**"Models download failing"**
```bash
# Check Ollama is running
ps aux | grep ollama

# Try downloading manually
ollama pull llama3.2:1b
```

**"Server won't start"**
```bash
# Verify all tests pass
python test_imports.py
python test_config.py
python test_system.py

# Check error logs
cat /tmp/ollama.log
```

---

## What Happens Next?

Once running, you can:

1. **Create Episodes**: Transform your 60 stories into YouTube episodes
2. **Generate Assets**: Get image prompts, dialogue scripts, metadata
3. **Batch Process**: Create multiple episodes in sequence
4. **Iterate**: Adjust bot configs and refine output

The system will:
- Index all your story files automatically
- Process requests through Claude orchestrator
- Coordinate 14 specialized bots in parallel
- Generate production-ready content packages

---

## Cost Per Episode

- Local processing (90%): **FREE** on your RTX 5090
- Claude orchestrator (10%): **~$2**
- **Total**: <$5 per episode
- **Savings**: 90-95% vs all-cloud ($50-200/episode)

---

**Ready? Start with Step 1:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

🚀 Let's create something amazing!
