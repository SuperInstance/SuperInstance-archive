# Setup Checklist - Content Studio

Use this checklist to ensure everything is properly configured.

## ☑ Python Environment

- [ ] Python 3.10+ installed
  ```bash
  python3 --version
  ```

- [ ] Virtual environment created
  ```bash
  ls venv/
  ```

- [ ] Dependencies installed ✓ (DONE - installed during setup)
  ```bash
  source venv/bin/activate
  pip list | grep -E "fastapi|anthropic|ollama"
  ```

## ☑ Ollama Setup

- [ ] Ollama installed
  ```bash
  ollama --version
  ```

- [ ] Ollama service running
  ```bash
  curl http://localhost:11434/api/tags
  # OR
  ps aux | grep ollama
  ```

- [ ] Models downloaded:
  - [ ] llama3.2:1b (1.3GB)
    ```bash
    ollama pull llama3.2:1b
    ```
  - [ ] llama3.2:3b (2.0GB)
    ```bash
    ollama pull llama3.2:3b
    ```
  - [ ] qwen2.5-coder:3b (1.9GB) [Optional but recommended]
    ```bash
    ollama pull qwen2.5-coder:3b
    ```

- [ ] Verify models
  ```bash
  ollama list
  # Should show all 3 models
  ```

## ☑ Configuration

- [ ] .env file created ✓ (DONE)
  ```bash
  ls -la .env
  ```

- [ ] Claude API key added
  ```bash
  # Edit .env file
  nano .env
  # Change: ANTHROPIC_API_KEY=your_real_key_here
  ```

- [ ] Get API key from: https://console.anthropic.com/

- [ ] Verify API key is set
  ```bash
  grep ANTHROPIC_API_KEY .env | grep -v "your_anthropic"
  # Should show your actual key
  ```

## ☑ Story Files

- [ ] Story files exist
  ```bash
  ls ~/Story_*_v3.md | wc -l
  # Should show 60
  ```

- [ ] If not in home directory, update .env:
  ```bash
  nano .env
  # Set STORY_SOURCE_PATH to correct location
  ```

## ☑ Directory Structure

All created ✓ (DONE during setup):
- [x] config/ - Configuration files
- [x] src/ - Python code
- [x] data/ - Data storage
- [x] venv/ - Virtual environment
- [x] .env - Environment variables

## ☑ Test System

- [ ] Start server
  ```bash
  ./start.sh
  # OR
  source venv/bin/activate && python -m src.orchestrator.main
  ```

- [ ] Should see:
  ```
  🚀 Initializing Loopless Content Studio...
  📚 Content bootcamp file loaded
  ✓ Created script_writer_1
  ... (more bots)
  ✅ Content Studio initialized successfully!
  📊 14 bots ready
  INFO:     Uvicorn running on http://0.0.0.0:8000
  ```

- [ ] Open new terminal and test status
  ```bash
  curl http://localhost:8000/api/status
  # Should return JSON with bot statuses
  ```

- [ ] Test simple request
  ```bash
  curl -X POST http://localhost:8000/api/request \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello", "user_id": "test"}' | jq
  ```

## ☑ GPU (Optional)

- [ ] NVIDIA drivers installed
  ```bash
  nvidia-smi
  # Should show your RTX 5090
  ```

- [ ] CUDA available (for future use)
  ```bash
  nvcc --version
  ```

## 🎯 Ready to Use!

Once all boxes are checked:

1. **Start the system**:
   ```bash
   ./start.sh
   ```

2. **Create your first episode**:
   ```bash
   curl -X POST http://localhost:8000/api/request \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Create Episode 1 for YouTube (28 minutes)",
       "user_id": "me"
     }' | jq
   ```

3. **Watch the bots work** in the server terminal

4. **Review the output** - bots will generate:
   - Adapted script with scenes
   - Image prompts for generation
   - Formatted dialogue
   - Sound design plan
   - YouTube metadata

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./start.sh` | Start Content Studio |
| `curl http://localhost:8000/api/status` | Check system status |
| `ollama list` | Show downloaded models |
| `nvidia-smi` | Check GPU usage |
| `cat COMMANDS.md` | See all commands |

## Troubleshooting

### Models not downloading?
```bash
# Check Ollama is running
ollama serve &
# Wait 3 seconds
sleep 3
# Try downloading again
ollama pull llama3.2:1b
```

### API key not working?
```bash
# Verify it's set correctly
cat .env | grep ANTHROPIC_API_KEY
# Test it
export ANTHROPIC_API_KEY="your-key-here"
python3 -c "import anthropic; print('API key works!')"
```

### Port 8000 in use?
```bash
# Find and kill the process
lsof -i :8000
kill $(lsof -t -i:8000)
```

### Stories not found?
```bash
# Find where they are
find ~ -name "Story_*_v3.md" -type f | head -5
# Update .env with correct path
nano .env
```

## Next Steps After Setup

1. Read **COMMANDS.md** - Quick command reference
2. Read **START_HERE.md** - System overview and architecture
3. Read **SETUP.md** - Detailed setup guide with troubleshooting
4. Read **BUILD_LOG.md** - See how the system was built

## Files You Might Need to Edit

- **.env** - API keys and configuration
- **config/content_bot_configs.yaml** - Bot settings
- **config/content_bootcamp.md** - Claude's system understanding

## Getting Help

If stuck:
1. Check **SETUP.md** troubleshooting section
2. Check **COMMANDS.md** for specific commands
3. Look at server logs for error messages
4. Verify each checkbox above is completed

---

**Current Status**: Python packages installed ✓, Ollama and models need manual installation

**Time to complete setup**: ~30 minutes (mostly waiting for model downloads)
