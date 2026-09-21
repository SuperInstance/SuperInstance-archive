# Offline / Transfer Setup - Content Studio

If you have a faster internet connection on another machine, you can download models there and transfer them. This is **much faster** than downloading on a slow connection!

---

## Option 1: Copy Ollama Models Directly (Recommended)

### On Fast Machine (Download Models)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start service
ollama serve &
sleep 3

# Download all 3 models
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:3b

# Verify downloaded
ollama list
```

### Find Model Files

Ollama stores models in: `~/.ollama/models/`

```bash
# Check size
du -sh ~/.ollama/models/
# Should show ~5.2GB

# Create tar archive for transfer
cd ~
tar -czf ollama-models.tar.gz .ollama/models/

# Check archive size
ls -lh ollama-models.tar.gz
# Should be ~5GB (compressed)
```

### Transfer to Your Content Studio Machine

**Option A: USB Drive**
```bash
# On fast machine
cp ollama-models.tar.gz /media/usb/

# On your machine
cp /media/usb/ollama-models.tar.gz ~/
```

**Option B: SCP (if machines on same network)**
```bash
# From fast machine to your machine
scp ollama-models.tar.gz yourusername@yourmachine:~/
```

**Option C: Cloud Transfer (Dropbox, Google Drive, etc.)**
- Upload `ollama-models.tar.gz` from fast machine
- Download on your machine

### Install on Your Machine

```bash
# 1. Install Ollama (if not already)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Stop Ollama if running
pkill ollama

# 3. Extract models
cd ~
tar -xzf ollama-models.tar.gz

# 4. Start Ollama
ollama serve &
sleep 3

# 5. Verify models are there
ollama list
# Should show all 3 models!

# 6. Test a model
ollama run llama3.2:1b "Hello"
```

---

## Option 2: Use Ollama Export/Import

### On Fast Machine

```bash
# Download models
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:3b

# Create exports directory
mkdir ~/ollama-exports

# Note: Ollama doesn't have built-in export yet
# So use Option 1 (copy models directory) instead
```

---

## Option 3: Download Model Files Directly

Ollama models are stored on Hugging Face. You can download them directly:

### llama3.2:1b
- Source: Meta Llama models
- Size: ~1.3GB
- Direct download not officially supported (use Option 1)

### llama3.2:3b
- Source: Meta Llama models
- Size: ~2.0GB
- Direct download not officially supported (use Option 1)

### qwen2.5-coder:3b
- Source: Qwen models
- Size: ~1.9GB
- Direct download not officially supported (use Option 1)

**Note**: Ollama uses a specific format (GGUF), so it's best to use Option 1.

---

## Recommended Workflow

**Best approach for slow internet:**

1. **On fast machine** (friend's computer, work, library, etc.):
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh

   # Download models (takes 10-15 min on fast connection)
   ollama serve &
   ollama pull llama3.2:1b
   ollama pull llama3.2:3b
   ollama pull qwen2.5-coder:3b

   # Create archive
   cd ~
   tar -czf ollama-models.tar.gz .ollama/models/

   # Copy to USB or upload to cloud
   cp ollama-models.tar.gz /media/usb/
   ```

2. **Transfer**: USB drive, cloud storage, or network transfer

3. **On your machine**:
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh

   # Extract models
   tar -xzf ollama-models.tar.gz -C ~

   # Start Ollama
   ollama serve &

   # Verify
   ollama list
   ```

4. **Continue setup**:
   ```bash
   cd /home/activeloguser/content-studio-dev
   nano .env  # Add API key
   ./start.sh
   ```

---

## File Sizes

```
llama3.2:1b         ~1.3 GB
llama3.2:3b         ~2.0 GB
qwen2.5-coder:3b    ~1.9 GB
------------------------
Total:              ~5.2 GB
Compressed (tar.gz): ~4.8 GB
```

---

## Time Savings

**Slow Connection (50 KB/s)**:
- Direct download: 40-50 minutes per model = **2-3 hours total**
- Fast machine + transfer: 10 min download + 10 min transfer = **20 minutes total**

**Savings**: ~2.5 hours! 🎉

---

## Alternative: Use Smaller Models

If transfer is also slow, you can use smaller models initially:

```bash
# On your machine - smaller, faster downloads
ollama pull llama3.2:1b  # Only 1.3GB - use for everything initially

# Later, add bigger models when you have time
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:3b
```

Then update `config/content_bot_configs.yaml` to use `llama3.2:1b` for all bots initially.

---

## Verification After Transfer

```bash
# 1. Check Ollama is installed
ollama --version

# 2. Start Ollama
ollama serve &

# 3. List models
ollama list
# Should show:
# NAME                    ID          SIZE
# llama3.2:1b            ...         1.3 GB
# llama3.2:3b            ...         2.0 GB
# qwen2.5-coder:3b       ...         1.9 GB

# 4. Test each model
ollama run llama3.2:1b "test"
ollama run llama3.2:3b "test"
ollama run qwen2.5-coder:3b "test"

# All should respond with text
```

---

## Troubleshooting

**"Models not showing up after transfer"**
```bash
# Check if files exist
ls -la ~/.ollama/models/

# Check permissions
chmod -R 755 ~/.ollama/

# Restart Ollama
pkill ollama
ollama serve &
ollama list
```

**"Model files corrupted"**
```bash
# Verify archive integrity
tar -tzf ollama-models.tar.gz | head

# Re-extract
rm -rf ~/.ollama/models/
tar -xzf ollama-models.tar.gz -C ~
```

**"Wrong directory structure"**
```bash
# Ollama expects: ~/.ollama/models/...
# Check structure in archive
tar -tzf ollama-models.tar.gz | head

# If it's .ollama/models/..., extract to home:
tar -xzf ollama-models.tar.gz -C ~

# If it's just models/..., fix it:
mkdir -p ~/.ollama
tar -xzf ollama-models.tar.gz -C ~/.ollama/
```

---

## After Models Are Installed

Continue with:
```bash
cd /home/activeloguser/content-studio-dev
nano .env  # Add Claude API key
./start.sh
```

Then test:
```bash
curl http://localhost:8000/api/status | jq
```

---

**This is the fastest way if you have slow internet!** 🚀
