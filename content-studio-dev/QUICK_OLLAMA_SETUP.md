# Quick Ollama Setup Guide

Since Ollama needs sudo privileges to install, here are the commands to run:

## Step 1: Install Ollama (requires sudo password)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Expected output:**
```
>>> Installing ollama to /usr/local
>>> Creating ollama user...
>>> Adding ollama user to render group...
>>> Adding ollama user to video group...
>>> Installing ollama service...
>>> Done!
```

## Step 2: Start Ollama Service

```bash
# Start in background
ollama serve > /tmp/ollama.log 2>&1 &

# Verify it's running
curl http://localhost:11434/api/tags
```

Should return JSON with empty models list: `{"models":[]}`

## Step 3: Download Models (Automated Script)

```bash
# Run our download script (downloads in background)
./download_models.sh
```

This will download all 3 models in background (~5.2GB total):
- llama3.2:1b (1.3GB) - ~5-10 minutes
- llama3.2:3b (2.0GB) - ~8-15 minutes
- qwen2.5-coder:3b (1.9GB) - ~7-12 minutes

**Total time**: 20-40 minutes depending on connection

## Monitor Progress

```bash
# Watch download progress
tail -f /tmp/ollama_downloads.log

# Check what's downloaded so far
ollama list
```

## Manual Installation (If Script Fails)

```bash
# Download one at a time
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:3b
```

## Verify Complete Setup

```bash
# Should show all 3 models
ollama list

# Test a model
ollama run llama3.2:1b "Hello, test"
```

## Quick Test

```bash
# After models are downloaded, test the system
cd /home/activeloguser/content-studio-dev
./start.sh
```

---

**While models download, you can work on:**
- Adding your Claude API key to `.env`
- Reading the documentation
- Testing code components that don't need models yet
